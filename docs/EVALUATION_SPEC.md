# drowsy_detection 評価エンジン 仕様書（更新版）

最終更新: 2025-09-22 (JST)

## 更新履歴

| 日付 | バージョン | 変更内容 |
|------|------------|----------|
| 2025-09-22 | 3.0.2 | **drowsy_detection自動更新機能追加**<br>• 評価実行前に最新版チェック・自動更新<br>• GitHubリポジトリから最新コミット確認<br>• 更新時はモジュール再読込とバージョン更新<br>• README・仕様書更新 |
| 2025-08-25 | 2.0.0 | 仕様書修正内容に基づく大幅改訂<br>• パス参照の削除（具体的なディレクトリパスを削除）<br>• database.dbのconfig化対応<br>• 出力形式の変更（summary.csv → JSON/YAML形式）<br>• 相対パスでの管理に変更 |
| 2025-08-22 | 1.0.0 | 初版作成<br>• 評価エンジンの基本仕様<br>• 実行フローと評価ロジック<br>• 生成物の定義 |

## 目的
- GitHub上のアルゴリズムパッケージ（`abekoki/drowsy_detection` を pip でインストール）を用いて、コアライブラリ出力CSVの各フレームを逐次判定し、アルゴリズム出力CSVを生成・DataWareHouseへ登録した上で、タグ区間に対する正誤判定と正解率を算出・記録する。

## 入力と前提
- 対象データスコープ: DataWareHouseから取得するコアライブラリ出力データ
- コアCSV → アルゴ入力（必須列マッピング）:
  - `frame` → `frame_num`
  - `leye_openness` → `left_eye_open` (0..1)
  - `reye_openness` → `right_eye_open` (0..1)
  - `confidence` → `face_confidence` (0..1)
- フレームレート: `30.0 fps` を使用（`DrowsyDetector.set_frame_rate(30.0)`）
- ground truth（期待値）: タグに記載の各区間はすべて「連続閉眼あり」= 1 とみなす

## 使用ライブラリ（確定）
- アルゴリズムパッケージ（GitHubの指定リポジトリから pip で最新をインストール）
  - クラス: `drowsy_detection.core.drowsy_detector.DrowsyDetector`
  - 入力: `InputData(frame_num, left_eye_open, right_eye_open, face_confidence)`
  - 出力: `OutputData(is_drowsy, frame_num, left_eye_closed, right_eye_closed, continuous_time, error_code)`
  - 設定: `Config` を使用。`set_frame_rate(30.0)` を呼ぶ。
  - バージョン: パッケージの `__version__` + 動的バージョニング
    - **動的バージョニング**: コミットハッシュベースでバージョンを動的生成
    - フォーマット: `{base_version}+{commit_hash[:8]}`（例: `0.1.1+fa5172ba`）
    - 新しいコミットが検出された場合、自動的にマイナーバージョンを更新
  - Gitハッシュ: 指定GitHubリポジトリの `git ls-remote HEAD` により最新コミット取得
- DataWareHouse（Python API）
  - 例: `list_core_lib_outputs(video_id=...)`, `get_video_tags(video_id)`, `create_algorithm_version(...)`, `create_algorithm_output(...)`

## 設定
- database.dbのパスはconfig化すること
- 設定ファイルでdatabase.dbのパスを管理し、相対パスでの参照を可能にする

## インストール（参考）
- uv 環境で GitHub のタグ（例: v0.1.0）を pip インストール
```bash
uv pip install git+https://github.com/abekoki/drowsy_detection.git@v0.1.0
```
- 詳細は GitHub の README を参照: [GitHub README](https://github.com/abekoki/drowsy_detection)

## 生成物
1) アルゴリズム出力（CSV, 動画ごと）
   - パス: DataWareHouseのdatabase.dbに相対パスで登録
   - ファイル名はデータベース上の `video_id` を使用（`video_name` は使用しない）
   - 列: `frame_num,is_drowsy,left_eye_closed,right_eye_closed,continuous_time,error_code`
   - DataWareHouse 登録:
     - `create_algorithm_version(version=__version__, update_info=..., commit_hash=<git hash>)`
     - `create_algorithm_output(algorithm_id, core_lib_output_id, algorithm_output_dir)`

2) 評価結果
   - バージョン別フォルダ: DataWareHouseのdatabase.dbに相対パスで登録
   - 評価結果サマリ（JSON/YAML形式）
     - 機械判読可能かつ人が見てもわかりやすい形式
     - 必須情報:
       - 評価条件のサマリ
       - データセット全体での正解率、正解数、タスク数
       - 各ビデオデータ別の正解率、正解数、タスク数
       - 各ビデオデータ評価結果へのリンク（パス）
   - `{video_id}.csv`（動画ごとの明細。ファイル名は `video_id`）
     - 列: `task_id,predicted,ground_truth,correct,notes`
   - **評価レポート（Markdown形式）** ⭐NEW⭐
     - ファイル名: `evaluation_report.md`
     - 人間が読みやすい可視化レポート
     - 内容:
       - 実行情報（日時、バージョン、コミットハッシュ）
       - 全体評価結果（正解率、評価ステータス）
       - ビデオ別評価結果（テーブル形式）
       - アルゴリズム検出統計（検出率、進捗バー）
       - 詳細結果（タスク別の予測・正解判定）
   - DataWareHouse 登録（評価結果のメタ登録）:
     - 方式: `datawarehouse.algorithm_api.create_algorithm_output(algorithm_id, core_lib_output_id, output_dir)` を準用
     - 運用: 評価結果のフォルダを `output_dir` として、各 `core_lib_output_id` と紐付けて登録
     - 備考: 評価結果はアルゴ出力に依存するため、同一 `algorithm_id` 配下に評価出力用の `algorithm_output` レコードとして保存（将来 `evaluation_output` テーブル新設時は置換）

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
   - 出力先: DataWareHouseのdatabase.dbに相対パスで登録
   - アルゴリズム `__version__` と `git rev-parse HEAD` を取得
   - **drowsy_detection最新版チェック**: リモートリポジトリから最新コミットを確認・自動更新
2) 対象データ取得
   - DataWareHouseからコアライブラリ出力対象の `core_lib_output` レコードを列挙
   - 対応する動画IDごとに `core_lib_output_dir` からCSVを取得
3) 推論とアルゴCSV出力
   - コアCSVを先頭から走査し、各フレームで `DrowsyDetector.update(InputData)` を呼び、行ごとに出力を蓄積
   - 動画ごとの結果をCSVファイルに保存
   - DataWareHouseにアルゴ出力を登録（アルゴバージョン→アルゴ出力）
4) 評価
   - `get_video_tags(video_id)` でタグ区間を取得
   - 手順3のアルゴCSVを読み、各タグ区間の `is_drowsy` を集計し `predicted` を算出
   - `ground_truth=1` と比較して `correct` を算出
   - 動画ごとに `{video_id}.csv` を出力
   - 全体集計を評価結果サマリ（JSON/YAML形式）に出力（当該バージョンのみ）
   - DataWareHouseに評価結果を登録:
     - 既存の `algorithm_id` を取得（なければ `create_algorithm_version`）
     - 各動画の `core_lib_output_id` を解決し、`create_algorithm_output(algorithm_id, core_lib_output_id, output_dir)` を呼ぶ
     - 必要に応じて `update_info` に評価実行のメタ情報（run_id, accuracy など）を付記
5) ログ
   - `log.md` に実行日時、対象件数、`overall_accuracy`、アルゴバージョン/ハッシュ、出力先を追記

## 例: 評価結果サマリ（JSON形式）
```json
{
  "evaluation_summary": {
    "run_id": "20250822-143000",
    "created_at": "2025-08-22T14:30:00",
    "algorithm_version": "0.1.0",
    "algorithm_commit_hash": "abc123def456",
    "evaluation_conditions": {
      "frame_rate": 30.0,
      "ground_truth": "all_tags_continuous_closed_eyes"
    },
    "overall_results": {
      "accuracy": 0.85,
      "total_num_correct": 17,
      "total_num_tasks": 20
    },
    "per_dataset": [
      {
        "video_id": "video_001",
        "accuracy": 0.8,
        "num_correct": 4,
        "num_tasks": 5,
        "result_file_path": "relative/path/to/video_001.csv"
      }
    ]
  }
}
```

## 例: {video_id}.csv（ヘッダ）
```
task_id,predicted,ground_truth,correct,notes
```

## エラー処理
- コアCSV読込失敗/フォーマット不整合 → 当該動画をスキップ、`notes` に理由
- アルゴ内部エラー → `error_code` をCSVに残す。評価時はエラーのみの区間はスキップ
- DataWareHouse登録失敗 → リトライの上、不可ならスキップし `log.md` に記録

## 追加メモ
- ファイル名は `video_id` を使用（`video_name` は使用しない）
- すべての入出力はDataWareHouseのdatabase.dbを基準とする相対パスで管理
- アルゴリズム出力結果や評価結果は、入力csvと同様に格納し、database.dbには相対パスで各出力結果のパスを登録
