# drowsy_detection 評価エンジン

![Version](https://img.shields.io/badge/version-3.0.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

drowsy_detectionアルゴリズムの性能評価を自動化するエンジンです。

## 🎯 概要

GitHub上の`abekoki/drowsy_detection`パッケージを使用して、コアライブラリ出力CSVから居眠り検出を実行し、タグ区間に基づく評価を行います。

## ✨ 主要機能

### 🔄 アルゴリズム評価
- GitHubパッケージの自動インストールと実行
- **最新版自動更新**: 評価実行前にdrowsy_detectionの最新版をチェック・更新
- フレーム単位でのリアルタイム居眠り検出
- DataWareHouseとの完全統合

### 📊 可視化レポート
- **マークダウンレポート自動生成** ⭐NEW⭐
- 視覚的な統計表示（進捗バー、絵文字）
- ビデオ別・タスク別の詳細結果
- 機械判読可能なJSON出力

### 🔧 バージョン管理
- **動的バージョニング**: `{base_version}+{commit_hash}`
- アルゴリズム更新の自動追跡
- 相対パスによる出力管理

## 🚀 クイックスタート

### 前提条件
- Python 3.10+
- uv (Python package manager)
- DataWareHouseデータベース

### インストール
```bash
# 仮想環境の作成と依存関係のインストール
uv venv
uv sync

# drowsy_detectionアルゴリズムのインストール
uv pip install git+https://github.com/abekoki/drowsy_detection.git
```

**📦 DataWareHouse統合**: `uv sync`で自動的にDataWareHouseパッケージがインストールされます。

### 実行
```bash
python main.py
```

### 設定
`config.yaml`で設定をカスタマイズ：
```yaml
datawarehouse:
  database_path: "../DataWareHouse/database.db"
  
output:
  base_dir: "../DataWareHouse/03_algorithm_output"
  evaluation_dir: "../DataWareHouse/04_evaluation_output"
  
algorithm:
  frame_rate: 30.0
  git_repo: "https://github.com/abekoki/drowsy_detection.git"
```

## 📝 生成される出力

### 1. アルゴリズム出力
- **ファイル**: `{video_id}.csv`
- **列**: `frame_num,is_drowsy,left_eye_closed,right_eye_closed,continuous_time,error_code`
- **場所**: `03_algorithm_output/v{version}/{run_id}/`

### 2. 評価結果
- **JSONサマリ**: `evaluation_summary.json`
- **詳細CSV**: `{video_id}.csv`（タスク別結果）
- **📊 マークダウンレポート**: `evaluation_report.md` ⭐NEW⭐

### 3. マークダウンレポートの特徴
- 🎯 全体評価結果（正解率、ステータス）
- 📊 ビデオ別統計テーブル
- 📈 検出率の視覚的表示
- 🔍 タスク別詳細分析
- 📝 実行情報（バージョン、コミットハッシュ）

## 🏗️ アーキテクチャ

```
evaluation_engine/
├── main.py              # メインエンジン
├── config.yaml          # 設定ファイル
├── docs/
│   └── EVALUATION_SPEC.md  # 詳細仕様書
├── CHANGELOG.md          # 更新履歴
└── README.md            # このファイル
```

## 🔄 ワークフロー

1. **最新版チェック**: drowsy_detectionのGitHubリポジトリから最新コミットをチェック・自動更新
2. **データ取得**: DataWareHouseからコアライブラリ出力を取得
3. **アルゴリズム実行**: drowsy_detectionでフレーム単位判定
4. **結果保存**: CSV形式でアルゴリズム出力を保存
5. **評価実行**: タグ区間に基づく正誤判定
6. **レポート生成**: JSON + Markdownでの結果出力
7. **データベース登録**: DataWareHouseへの結果登録

## 📊 評価指標

- **正解率**: タグ区間での予測精度
- **検出率**: フレーム単位での居眠り検出率
- **タスク別分析**: 区間ごとの詳細評価

## 🛠️ 技術仕様

- **言語**: Python 3.10+
- **パッケージ管理**: uv
- **アルゴリズム**: drowsy_detection (GitHub)
- **データベース**: DataWareHouse SQLite (pipパッケージ)
- **DataWareHouse**: v0.1.0 (remake_pip_lib)
- **設定**: YAML
- **出力**: CSV, JSON, Markdown

## 📚 ドキュメント

- [詳細仕様書](docs/EVALUATION_SPEC.md)
- [更新履歴](CHANGELOG.md)
- [drowsy_detectionアルゴリズム](https://github.com/abekoki/drowsy_detection)

## 🤝 貢献

1. Forkしてください
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. コミット (`git commit -m 'Add some AmazingFeature'`)
4. プッシュ (`git push origin feature/AmazingFeature`)
5. Pull Requestを開いてください

## 📜 ライセンス

MIT License

## 🏷️ バージョン

現在のバージョン: **3.0.2**

- **drowsy_detection自動更新機能追加** ⭐NEW⭐
- マークダウンレポート機能追加
- 動的バージョニング対応
- drowsy_detection v0.1.1対応
