# Changelog - drowsy_detection 評価エンジン

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.2] - 2025-09-22

### 🎉 Added
- **drowsy_detection自動更新機能**: 評価実行前の最新版チェック・自動更新
  - GitHubリポジトリから最新コミット確認
  - 新しいコミットがある場合の自動pip install
  - モジュール再読込による即時反映
  - バージョン情報の動的更新

### 🚀 Improved
- **実行準備プロセスの強化**:
  - アルゴリズム更新チェックの実行準備フェーズへの統合
  - 更新時の詳細なログ出力
  - エラーハンドリングの改善

### 📚 Documentation
- READMEの機能説明更新
- 仕様書の実行フロー更新
- ワークフロー図の更新

## [3.0.1] - 2025-09-22

### 🔧 Fixed
- **DataWareHouse pipパッケージ対応**:
  - remake_pip_libブランチの正式対応
  - uv syncでの自動インストール
  - ローカルパス参照の除去

## [3.0.0] - 2025-08-26

### 🎉 Added
- **マークダウンレポート機能**: 評価結果の可視化レポート自動生成
  - 実行情報（日時、バージョン、コミットハッシュ）の表示
  - 全体評価結果の視覚的サマリー
  - ビデオ別評価結果テーブル
  - アルゴリズム検出統計（進捗バー付き）
  - タスク別詳細結果（予測・正解判定）
  - 絵文字とカラーコードによる視覚的改善

- **動的バージョニングシステム**:
  - コミットハッシュベースのバージョン自動生成
  - フォーマット: `{base_version}+{commit_hash[:8]}`
  - アルゴリズム更新の自動検出と追跡

### 🔧 Fixed
- **データベース登録の相対パス問題**: 
  - `algorithm_output_table`への登録時に正しい相対パスを使用
  - DataWareHouse仕様に準拠した相対パス管理

### 🚀 Improved
- **drowsy_detection v0.1.1対応**:
  - 新しい閾値設定の対応
  - 改善されたアルゴリズムロジックの活用
  - より高精度な居眠り検出

### 📚 Documentation
- 仕様書の包括的更新（マークダウンレポート機能追加）
- CHANGELOGの新規作成
- READMEの更新

## [2.0.0] - 2025-08-25

### 🔧 Changed
- パス参照の削除（具体的なディレクトリパスを削除）
- database.dbのconfig化対応
- 出力形式の変更（summary.csv → JSON/YAML形式）
- 相対パスでの管理に変更

## [1.0.0] - 2025-08-22

### 🎉 Added
- 評価エンジンの初版作成
- 基本的な評価仕様とロジック
- 実行フローの定義
- 生成物の仕様定義

---

## Legend
- 🎉 Added: 新機能
- 🔧 Fixed: バグ修正
- 🚀 Improved: 改善
- 📚 Documentation: ドキュメント更新
- ⚠️ Deprecated: 非推奨機能
- 🗑️ Removed: 削除された機能
