# drowsy_detection 評価エンジン 仕様書（更新版）

最終更新: 2025-08-22 (JST)

## 目的
- アルゴリズムライブラリ `../drowsy_detection` を用いて、コアライブラリ出力CSV（`../DataWareHouse/02_core_lib_output/...`）の各フレームを逐次判定し、アルゴリズム出力CSVを生成・DataWareHouseへ登録した上で、タグ区間に対する正誤判定と正解率を算出・記録する。

## 入力と前提
- 対象データスコープ: `../DataWareHouse/02_core_lib_output` に存在するデータ（DataWareHouseから取得）
- コアCSV → アルゴ入力（必須列マッピング）:
  - `frame` → `frame_num`
  - `leye_openness` → `left_eye_open` (0..1)
  - `reye_openness` → `right_eye_open` (0..1)
  - `confidence` → `face_confidence` (0..1)
- フレームレート: `30.0 fps` を使用（`DrowsyDetector.set_frame_rate(30.0)`）
- ground truth（期待値）: タグに記載の各区間はすべて「連続閉眼あり」= 1 とみなす

## 使用ライブラリ（確定）
- `../drowsy_detection`:
  - クラス: `drowsy_detection.core.drowsy_detector.DrowsyDetector`
  - 入力: `InputData(frame_num, left_eye_open, right_eye_open, face_confidence)`
  - 出力: `OutputData(is_drowsy, frame_num, left_eye_closed, right_eye_closed, continuous_time, error_code)`
  - 設定: `Config` を使用。`set_frame_rate(30.0)` を呼ぶ。
  - バージョン: `drowsy_detection.__version__`（例: 0.1.0）
  - Gitハッシュ: drowsy_detectionリポジトリで `git rev-parse HEAD` により取得
- `../DataWareHouse`（Python API）
  - 例: `list_core_lib_outputs(video_id=...)`, `get_video_tags(video_id)`, `create_algorithm_version(...)`, `create_algorithm_output(...)`

## 生成物
1) アルゴリズム出力（CSV, 動画ごと）
   - パス: `../DataWareHouse/03_algorithm_output/{algorithm_version}/{video_name}_result.csv`
     - `{algorithm_version}` は `drowsy_detection.__version__`
   - 列: `frame_num,is_drowsy,left_eye_closed,right_eye_closed,continuous_time,error_code`
   - DataWareHouse 登録:
     - `create_algorithm_version(version=__version__, update_info=..., commit_hash=<git hash>)`
     - `create_algorithm_output(algorithm_id, core_lib_output_id, algorithm_output_dir)`

2) 評価結果（CSV）
   - `results/{run_id}/summary.csv`
     - 必須列: `overall_accuracy,total_num_correct,total_num_tasks`
     - 推奨列: `run_id,created_at,algorithm_version,algorithm_commit_hash,per_dataset`
   - `results/{run_id}/{data_name}.csv`（データ名=動画名など）
     - 列: `task_id,predicted,ground_truth,correct,notes`

## 評価ロジック
- 予測の集約（タグ区間 -> 1タスクの予測）
  - 区間内に `is_drowsy == 1` のフレームが1つでもあれば `predicted = 1`、なければ `0`
- ground_truth: 常に `1`（すべてのタグ区間が「連続閉眼あり」）
- 正解判定: `correct = (predicted == ground_truth)`
- 正解率: `accuracy = num_correct / num_tasks`
- 欠損・失敗: アルゴ出力が得られないフレームや区間は分母から除外し、`notes` に理由を記載

## 実行フロー（Step by Step）
1) 実行準備
   - `run_id` 発行（例: YYYYMMDD-HHMMSS）
   - 出力先: `results/{run_id}/`
   - `drowsy_detection.__version__` と `git rev-parse HEAD` を取得
2) 対象データ取得
   - DataWareHouseから `02_core_lib_output` 対象の `core_lib_output` レコードを列挙
   - 対応する動画IDごとに `core_lib_output_dir` からCSVを取得
3) 推論とアルゴCSV出力
   - コアCSVを先頭から走査し、各フレームで `DrowsyDetector.update(InputData)` を呼び、行ごとに出力を蓄積
   - 動画ごとの結果を `03_algorithm_output/{algorithm_version}/{video_name}_result.csv` に保存
   - DataWareHouseにアルゴ出力を登録（アルゴバージョン→アルゴ出力）
4) 評価
   - `get_video_tags(video_id)` でタグ区間を取得
   - 手順3のアルゴCSVを読み、各タグ区間の `is_drowsy` を集計し `predicted` を算出
   - `ground_truth=1` と比較して `correct` を算出
   - 動画ごとに `{data_name}.csv` を出力
   - 全体集計を `summary.csv` に出力
5) ログ
   - `log.md` に実行日時、対象件数、`overall_accuracy`、アルゴバージョン/ハッシュ、出力先を追記

## 例: summary.csv（ヘッダ）
```
overall_accuracy,total_num_correct,total_num_tasks,run_id,created_at,algorithm_version,algorithm_commit_hash,per_dataset
```

## 例: data_name.csv（ヘッダ）
```
task_id,predicted,ground_truth,correct,notes
```

## エラー処理
- コアCSV読込失敗/フォーマット不整合 → 当該動画をスキップ、`notes` に理由
- アルゴ内部エラー → `error_code` をCSVに残す。評価時はエラーのみの区間はスキップ
- DataWareHouse登録失敗 → リトライの上、不可ならスキップし `log.md` に記録

## 追加メモ
- `video_name` は `video_table.video_dir` からファイル名を抽出（拡張子除去）
- パスは DataWareHouseの仕様に合わせ、DB基準の相対パスで統一
- 表示時の丸め: 小数第4位で四捨五入（内部は倍精度）
