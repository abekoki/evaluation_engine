# アルゴリズムライブラリの評価仕様書作成
_Exported on 8/22/2025 at 13:55:25 GMT+9 from Cursor (1.4.5)_

---

**User**

このリポジトリは、アルゴリズムライブラリ"../drowsy_detection"の評価を実施するエンジンのリポジトリです。
ライブラリの仕様書と、 入力想定のサンプルcsv@core_lib_output_sample.csvを確認し、評価仕様を検討して。
最終的には各csvデータの各々の正解率と、データ全体の正解率を算出し、記録に残したい。
データ全体の正解率： summary.csv
全体の正解率、個別データの正解数とそうタスク数を記載。
個別データの状態：data_name.csv
- 各タスク毎の正解/不正解を記載。


csvや該当するタスクtagのデータは、"../DataWareHouse"で管理されています。API仕様を確認し、データ参照してください。

まずは状況確認し、仕様書をステップ倍ステップで作成してみましょう

---

**Cursor**

I'll start by creating a TODO plan and then draft the initial evaluation specification and project scaffolding files. Next, I'll write `.gitignore`, `.serena/README.md`, `log.md` with today's date, and `docs/EVALUATION_SPEC.md`. Then I'll mark the initial tasks complete and share key open questions to align specs.

I'll draft the evaluation spec first, then scaffold the repo files. After that, I’ll mark the spec task done, switch to scaffolding, create `.gitignore`, `.serena/README.md`, and `log.md`, then move on to confirming APIs and ask you targeted questions.

I’m going to activate the project, create the spec draft, then scaffold `.gitignore`, `.serena/README.md`, and `log.md`. After that, I’ll switch to the DataWareHouse project to locate its API/README files.

I'll add a dated entry to `log.md`, mark scaffolding complete, then switch to the `DataWareHouse` project to locate its API docs and README files. Next, I'll scan likely docs in parallel.

I'll review the DataWareHouse API and modules to confirm how to enumerate datasets, tasks, and ground-truth tags. Then I’ll extract the minimal interfaces we need and reconcile the spec.

I'll scan the DataWareHouse project files to confirm dataset/task/tag APIs and example usage.

I’m going to scan the DataWareHouse design docs and example modules to confirm how to retrieve videos, tasks, and tags, and how CSV output paths are structured. Then I’ll reconcile the spec and list concrete API calls we’ll use.

I'll switch back to the Improve_algorithm_development project, then create `.serena` under `evaluation_engine` and correct `.gitignore` to only contain `.venv/` per your rule.

- Created `evaluation_engine/docs/EVALUATION_SPEC.md` (draft), set up `.serena/`, `.gitignore`, and added `log.md` with timestamped init entry.
- Scanned `../DataWareHouse` APIs to confirm how to fetch tasks/tags and core-lib outputs.

### 提案: 評価仕様（ドラフト要点）
- 評価目的: `../drowsy_detection` の推論を、各CSV（≒各動画/データセット）ごと・全体で正解率集計。
- 入力データ:
  - コアライブラリの出力CSV群（`../DataWareHouse/02_core_lib_output/...`）。サンプルは `evaluation_engine/core_lib_output_sample.csv`。
  - 正解（GT）は `DataWareHouse` のタグ情報（`tag_table`）を使用。各タグはタスクIDと区間 `[start, end)` を持つ。
- 出力:
  - `results/{run_id}/summary.csv`: 全体正解率（overall_accuracy）、合計正解数/タスク数、データセット別の集計を格納。
  - `results/{run_id}/{data_name}.csv`: 各データセット（例: 各動画）ごとの明細。必須列: `task_id, predicted, ground_truth, correct`（任意: `confidence, notes`）。
- 正解判定:
  - `correct = (predicted == ground_truth)`。分母は有効タスク数（欠損/失敗は除外し別途 `skipped` 集計）。
- 処理フロー:
  1) DataWareHouseから対象動画/タスク/タグを取得
  2) 動画に紐づくコア出力ディレクトリ `core_lib_output_dir` を取得→CSV読込
  3) `drowsy_detection` に入力→`predicted` と `confidence` 取得
  4) タグごとにGTと突合→各データCSV出力、全体集計→`summary.csv`
  5) `log.md` に実行結果を追記（JST）

### DataWareHouseで利用予定のAPI（確認済み）
- ビデオ/タグ/タスク参照:
  - `datawarehouse.video_api.list_videos(...)`, `get_video(...)`
  - `datawarehouse.tag_api.get_video_tags(video_id)`, `list_tags(...)`
  - `datawarehouse.task_api.get_task(task_id)`, `list_tasks(...)`
- コア出力の参照:
  - `datawarehouse.core_lib_api.list_core_lib_outputs(video_id=...)` → `core_lib_output_dir` からCSVを取得
- 補助:
  - `datawarehouse.analytics_api.search_task_executions(...)`（条件抽出に活用可）

### 要確認事項（合意したら仕様に反映）
1) drowsy_detectionのI/F
   - 入力: コア出力CSVをそのまま渡すのか、前処理/列の指定は？（例: 開閉度・yaw等どれを使うか）
   - 出力: ラベル名（例: “drowsy”/“not_drowsy”）と `confidence` の定義。
   - 出力がフレーム単位/区間単位のどちらか。フレーム単位ならタグ区間内の集約方式（多数決/平均しきい値）を決める。
2) 評価対象の粒度
   - 「data_name」は動画単位で良いか。ファイル名 or `video_table.video_dir` からの命名規則を指定したい。
3) タスクとラベルの対応
   - GTは `tag.task_ID` 由来。`task_name` と推論ラベルの対応表が必要（例: “drowsy”タスクのみ評価？複数タスク？）。
4) データスコープ
   - 評価対象の動画/期間/タスクセットの範囲（全件 or 絞り込み条件）。
5) 出力フォーマットの詳細
   - `summary.csv` に含めるJSON列（`per_dataset`）の要/不要、精度表示の小数位（提案: 表示は小数第4位丸め）。

### 次アクション（同意後すぐ実装可）
- ランナー実装（uv環境でCLI/モジュール化）
  - DataWareHouseからデータ収集→`drowsy_detection` 呼び出し→CSV出力→`log.md`追記。
- `drowsy_detection` のAPI読み込み部分はアダプタ設計（将来のI/F変化に対応）。
- サンプル実行で `results/{run_id}/summary.csv` と各 `data_name.csv` を生成。

不足点/不明点への回答をお願いします:
- drowsy_detectionのAPI仕様（関数名、入出力、単位）を共有いただけますか？こちらで `../drowsy_detection` を参照して同定してもよいですか？
- 評価するラベルの種類と、`task_name` との対応表はありますか？
- 対象データの抽出条件（例: 全動画 or 指定日付範囲/被験者/タスクセット）を教えてください。
- `summary.csv` に含めたい追加列（バージョン情報、実行環境など）はありますか？

- 作業は `evaluation_engine/docs/EVALUATION_SPEC.md` に反映済み。合意後、評価ランナー実装に着手します。

- まとめ
  - 仕様ドラフト作成、`.serena/` と `.gitignore` 準備、`log.md` 追記済み。
  - DataWareHouseのAPIで動画→タグ→コア出力→CSVの参照ルートを確認。
  - 未確定は `drowsy_detection` のI/Fとラベル・集約ルール。

---

**User**

drowsy_detectionにcsv読み込み機能はないため、必要な列を抽出し、ライブラリにinputして。
評価は以下の流れで行われる認識です。
　コアライブラリのcsvを取得
　各フレームをdrowsy_detectionにinputし、出力結果を得る
　出力結果をcsvとして、DataWareHouseの03_algorithm_outputフォルダに格納・データベースに登録
　03_algorithm_outputに出力した結果をもとに、正解率や各データ内のタスクに対する正誤判定実施し、評価結果として出力

データスコープは、02_core_lib_outputに存在するデータ。
drowsy_detectionのAPI仕様（関数名、入出力、単位）は ../drowsy_detection を参照して。
評価するラベルとは何のことですか？


---

**Cursor**

I'll open the `../drowsy_detection` project to confirm its API, then update the spec accordingly and answer what “label” means in this context.

- drowsy_detectionのAPIを確認し、必要列のマッピングと評価フローを確定しました。次に仕様書に反映します。

### 仕様（更新案）
- 必須入力列の対応（core出力CSV → drowsy_detection.InputData）
  - frame → frame_num
  - leye_openness → left_eye_open [0..1]
  - reye_openness → right_eye_open [0..1]
  - confidence → face_confidence [0..1]
  - fpsは既定で30.0を使用予定（要確認）

- 実行フロー（ご提示の手順に準拠）
  1) DataWareHouseの`core_lib_output`一覧からスコープ対象（`02_core_lib_output`に存在）の各動画を取得
  2) 各動画のcore出力CSVを走査し、各フレームについて`DrowsyDetector.update(InputData)`を呼ぶ
     - クラス: `drowsy_detection.core.drowsy_detector.DrowsyDetector`
     - 入出力: `InputData(frame_num,left_eye_open,right_eye_open,face_confidence)` → `OutputData(is_drowsy,frame_num,left_eye_closed,right_eye_closed,continuous_time,error_code)`
     - 初期化: `Config`読込、`set_frame_rate(fps)`実行
  3) 各動画ごとにアルゴリズム出力CSVを作成し、`03_algorithm_output/<run_id>/<video_name>_result.csv`へ保存
     - 列: frame_num,is_drowsy,left_eye_closed,right_eye_closed,continuous_time,error_code
  4) DataWareHouseへ登録
     - `create_algorithm_version(version, update_info, commit_hash, base_version_id?)`
     - `create_algorithm_output(algorithm_id, core_lib_output_id, algorithm_output_dir)`
  5) 評価
     - `get_video_tags(video_id)`で各タスク区間[start,end)を取得
     - 各タスク区間のフレームの`is_drowsy`を集計してウィンドウ予測を算出
       - 既定: ウィンドウ内に`is_drowsy==1`が1つでもあれば predicted=1、なければ0
     - ground_truthはタスクに対する期待値（後述の「ラベル」）を用いる
     - データ別: `results/{run_id}/{data_name}.csv`（task_id,predicted,ground_truth,correct,...）
     - 全体: `results/{run_id}/summary.csv`（overall_accuracy,total_num_correct,total_num_tasks,run_id,created_at,per_dataset）

### 「評価するラベル」とは？
- 定義: 各タスク区間に対し、アルゴリズムが「眠気（連続閉眼）を検知すべきか否か」の期待クラス（ground_truth）です。  
  - 例: 「連続閉眼」タスクなら ground_truth=1（検知すべき）、それ以外（非眠気）のタスクなら ground_truth=0（検知すべきでない）。

- 確認したい点
  1) どの`task_name`/`task_ID`を「眠気あり(1)」とみなしますか？（マッピング表をご提示ください）
     - 例: task_nameに「閉眼」「drowsy」を含むもの→1、それ以外→0 など
  2) fpsは30でよいですか？（core出力CSVのフレームレート情報が見当たらなかったため）
  3) `drowsy_detection`のversion/commit_hashの登録方法
     - versionは`pyproject.toml`に準拠、commit_hashはGitから取得でよいか（指定あれば共有ください）

上記で問題なければ、`docs/EVALUATION_SPEC.md`を更新し、ランナー実装（CSV読込→フレーム逐次推論→03出力保存→DB登録→評価CSV出力）に着手します。

---

**User**

3) 各動画ごとにアルゴリズム出力CSVを作成し、03_algorithm_output/<run_id>/<video_name>_result.csvへ保存
列: frame_num,is_drowsy,left_eye_closed,right_eye_closed,continuous_time,error_code
→<run_id>ではなくアルゴリズムバージョンをフォルダ名にして。

taskに記載のtag区間はすべて「連続閉眼あり」が期待値です

fpsは30です。

hashはgitから取得して。




---

**Cursor**

I’ll fetch the drowsy_detection package version sources to confirm how we’ll obtain the version programmatically, then update the evaluation spec with your clarifications (algorithm output path uses version folder, all tag intervals are ground-truth=1, fps=30, git hash from repo). Next, I’ll record this in log.md.

I’ll update the spec per your clarifications, then append a dated entry to log.md.

I'll read the current spec and log, then update `evaluation_engine/docs/EVALUATION_SPEC.md` with your clarifications and append a dated note to `log.md`.

I'll update the spec file with your clarifications and append a dated note to log.md, then mark the spec update task complete.

- 仕様を更新しました。アルゴ出力は `03_algorithm_output/{algorithm_version}/{video_name}_result.csv`、タグ区間のGT=1、fps=30、gitハッシュ取得を明記。`evaluation_engine/docs/EVALUATION_SPEC.md` と `log.md` に反映済み。

### 次実装の確認事項
- **アルゴバージョン/ハッシュ**: `drowsy_detection.__version__` と `git rev-parse HEAD`（`drowsy_detection` リポ上）で取得し、DataWareHouseへ登録します。
- **予測集約**: タグ区間内に `is_drowsy==1` が1つでもあれば predicted=1。問題なければこのルールで実装します。
- **保存パス**: DataWareHouseの相対パス規約に合わせます（DB位置起点）。`video_name` は `video_dir` のファイル名から拡張子を除去して生成。

実装に進めてよいですか？進める場合、評価ランナー（CSV読込→逐次推論→03出力→DB登録→評価CSV生成）を作成します。

---

**User**

問題ないです。

---

**Cursor**

I'll quickly read the drowsy_detection Config to understand required parameters before implementing the runner, then create the evaluation runner script that reads core CSVs, runs the detector per frame, writes algorithm outputs under versioned folder, registers them in DataWareHouse, and generates evaluation CSVs.

I'll add a task to implement the evaluation runner, then create the runner script and helper with the described flow, and log the scaffolding.

I'll implement the evaluation runner script and supporting code, then update the log with a timestamped entry.

- ランナー `evaluation_engine/run_evaluation.py` を実装しました。core出力→逐次推論→`03_algorithm_output/{algorithm_version}/{video_name}_result.csv` 保存→DataWareHouse登録→評価CSV出力（各`data_name.csv`と`summary.csv`）まで実行します。
- `README.md` 追記と `log.md` へ記録済み。

実行方法:
- Windows PowerShell:
```powershell
uv run python evaluation_engine/run_evaluation.py
```

補足:
- `drowsy_detection.__version__` と `git rev-parse HEAD` でバージョンとハッシュ取得。
- FPS=30固定。タグ区間はGT=1。区間内に1フレームでも `is_drowsy==1` があれば predicted=1。
- DataWareHouseへの登録は `create_algorithm_version`（未登録時のみ）→`create_algorithm_output` を実行。
- `02_core_lib_output` のCSVはフォルダ直下のCSVを優先（名称に`analysis`を含むものを優先選択）。

このまま実行して結果を確認しますか？

```powershell
uv run python evaluation_engine/run_evaluation.py
```

