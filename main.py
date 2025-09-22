#!/usr/bin/env python3
"""
drowsy_detection 評価エンジン メイン実装

仕様書: docs/EVALUATION_SPEC.md に基づく評価エンジン
"""

import sys
import os
import json
import yaml
import pandas as pd
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# DataWareHouseパッケージのインポート
import datawarehouse as dwh
from drowsy_detection import DrowsyDetector, InputData, OutputData, Config
import drowsy_detection


class EvaluationEngine:
    """評価エンジンメインクラス"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        評価エンジンの初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = self._load_config(config_path)
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.db_path = os.path.abspath(self.config['datawarehouse']['database_path'])
        
        # 出力ディレクトリの設定
        self.output_base_dir = Path(self.config['output']['base_dir'])
        self.evaluation_dir = Path(self.config['output']['evaluation_dir'])
        
        # アルゴリズム情報の取得
        self.algorithm_commit_hash = self._get_algorithm_commit_hash()
        # drowsy_detectionのバージョンをコミットハッシュで動的生成
        self.algorithm_version = self._get_dynamic_version(drowsy_detection.__version__, self.algorithm_commit_hash)
        # アルゴリズムID（登録後に保持し、評価登録で使用）
        self.algorithm_id: Optional[int] = None
        
        print(f"[{self.run_id}] 評価エンジン初期化完了")
        print(f"  Database: {self.db_path}")
        print(f"  Algorithm version: {self.algorithm_version}")
        print(f"  Algorithm commit hash: {self.algorithm_commit_hash}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗: {e}")
            raise
    
    def _get_algorithm_commit_hash(self) -> str:
        """アルゴリズムのGitコミットハッシュを取得"""
        try:
            result = subprocess.run(
                ["git", "ls-remote", self.config['algorithm']['git_repo'], "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\t')[0]
            else:
                return "unknown"
        except Exception:
            return "unknown"

    def _check_and_update_algorithm(self) -> str:
        """drowsy_detectionの最新版を確認・更新し、新しいコミットハッシュを返す"""
        try:
            print(f"[{self.run_id}] drowsy_detectionの更新チェック中...")

            # リモートリポジトリの最新コミットハッシュを取得
            result = subprocess.run(
                ["git", "ls-remote", self.config['algorithm']['git_repo'], "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print(f"[{self.run_id}] リモートコミット取得失敗、現在のバージョンを使用")
                return self.algorithm_commit_hash

            remote_commit = result.stdout.strip().split('\t')[0]

            # 現在のコミットハッシュと比較
            if remote_commit == self.algorithm_commit_hash:
                print(f"[{self.run_id}] drowsy_detectionは最新版です (commit: {remote_commit[:8]})")
                return remote_commit

            # 新しいコミットがある場合、更新を試行
            print(f"[{self.run_id}] 新しいコミットが見つかりました: {remote_commit[:8]} (現在: {self.algorithm_commit_hash[:8]})")
            print(f"[{self.run_id}] drowsy_detectionを更新中...")

            # pip installで最新版をインストール
            install_result = subprocess.run(
                ["uv", "pip", "install", f"git+{self.config['algorithm']['git_repo']}", "--quiet"],
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )

            if install_result.returncode == 0:
                print(f"[{self.run_id}] drowsy_detection更新完了")
                # モジュールをリロードして新しいバージョンを反映
                import importlib
                importlib.reload(drowsy_detection)

                # 新しいバージョンを取得してインスタンス変数を更新
                new_version = drowsy_detection.__version__
                self.algorithm_version = self._get_dynamic_version(new_version, remote_commit)
                self.algorithm_commit_hash = remote_commit

                print(f"[{self.run_id}] バージョン更新: {self.algorithm_version}")
                return remote_commit
            else:
                print(f"[{self.run_id}] 更新失敗、使用可能な最新コミットを使用: {remote_commit[:8]}")
                return remote_commit

        except Exception as e:
            print(f"[{self.run_id}] drowsy_detection更新チェックエラー: {e}")
            return self.algorithm_commit_hash

    def _get_dynamic_version(self, base_version: str, commit_hash: str) -> str:
        """コミットハッシュベースで動的バージョンを生成"""
        if commit_hash == "unknown" or not commit_hash:
            return base_version
        
        # コミットハッシュの最初の8文字を使用
        short_hash = commit_hash[:8]
        
        # ベースバージョンが0.1.0で、新しいコミットがある場合は0.1.1として扱う
        if base_version == "0.1.0" and commit_hash != "e3803bb59fc690e096f82af4e7ba4aff235537ac":
            return f"0.1.1+{short_hash}"
        
        return f"{base_version}+{short_hash}"
    
    def run_evaluation(self) -> bool:
        """評価エンジンのメイン実行"""
        try:
            print(f"\n[{self.run_id}] 評価開始")
            
            # 1. 実行準備
            self._prepare_execution()
            
            # 2. 対象データ取得
            core_outputs = self._get_target_data()
            
            # 3. 推論とアルゴCSV出力
            algorithm_results = self._run_algorithm_inference(core_outputs)
            
            # 4. 評価
            evaluation_results = self._run_evaluation_logic(algorithm_results)
            
            # 5. 評価結果をDBへ登録（新API対応）
            register_summary = self._register_evaluation_to_db(algorithm_results, evaluation_results)
            
            # 6. ログ出力
            self._write_log(evaluation_results, register_summary)
            
            print(f"\n[{self.run_id}] 評価完了")
            return True
            
        except Exception as e:
            print(f"\n[{self.run_id}] 評価エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _prepare_execution(self):
        """実行準備"""
        print(f"[{self.run_id}] 実行準備中...")

        # drowsy_detectionの最新版チェックと更新
        self._check_and_update_algorithm()

        # 出力ディレクトリの作成
        version_dir = self.output_base_dir / f"v{self.algorithm_version}"
        self.run_output_dir = version_dir / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)
        
        evaluation_version_dir = self.evaluation_dir / f"v{self.algorithm_version}"
        self.evaluation_output_dir = evaluation_version_dir / self.run_id
        self.evaluation_output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  出力ディレクトリ: {self.run_output_dir}")
        print(f"  評価ディレクトリ: {self.evaluation_output_dir}")
    
    def _get_target_data(self) -> List[Dict[str, Any]]:
        """対象データの取得"""
        print(f"[{self.run_id}] 対象データ取得中...")
        
        try:
            core_outputs = dwh.list_core_lib_outputs(db_path=self.db_path)
            print(f"  取得件数: {len(core_outputs)}")
            
            for output in core_outputs[:3]:  # 最初の3件を表示
                print(f"    ID={output['core_lib_output_ID']}, "
                      f"video_ID={output['video_ID']}, "
                      f"dir={output['core_lib_output_dir']}")
            
            return core_outputs
            
        except Exception as e:
            print(f"  データ取得エラー: {e}")
            raise
    
    def _run_algorithm_inference(self, core_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推論とアルゴCSV出力"""
        print(f"[{self.run_id}] アルゴリズム推論実行中...")
        
        results = []
        
        # アルゴリズムバージョンの登録
        try:
            algorithm_id = dwh.create_algorithm_version(
                version=self.algorithm_version,
                update_info=f"評価エンジン実行 run_id={self.run_id}",
                commit_hash=self.algorithm_commit_hash,
                db_path=self.db_path
            )
            print(f"  アルゴリズムバージョン登録: ID={algorithm_id}")
        except dwh.DWHUniqueConstraintError:
            # 既存のコミットハッシュから検索
            existing = dwh.find_algorithm_by_commit_hash(self.algorithm_commit_hash, db_path=self.db_path)
            if existing:
                algorithm_id = existing['algorithm_ID']
                print(f"  既存アルゴリズムバージョン使用: ID={algorithm_id}")
            else:
                print(f"  エラー: 既存のアルゴリズムが見つかりません")
                return []
        # 後続の評価登録で使用するため保持
        self.algorithm_id = algorithm_id
        
        for core_output in core_outputs:
            try:
                result = self._process_single_video(core_output, algorithm_id)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ビデオ処理エラー (ID={core_output['video_ID']}): {e}")
                continue
        
        print(f"  処理完了: {len(results)}件")
        return results
    
    def _process_single_video(self, core_output: Dict[str, Any], algorithm_id: int) -> Optional[Dict[str, Any]]:
        """単一ビデオの処理"""
        video_id = core_output['video_ID']
        core_lib_output_id = core_output['core_lib_output_ID']
        
        print(f"    ビデオID={video_id} 処理中...")
        
        # コアCSVファイルの読み込み
        core_dir = Path(self.db_path).parent / core_output['core_lib_output_dir']
        csv_files = list(core_dir.glob("*.csv"))
        
        if not csv_files:
            print(f"      CSVファイルが見つかりません: {core_dir}")
            return None
        
        core_csv_path = csv_files[0]  # 最初のCSVファイルを使用
        
        try:
            df = pd.read_csv(core_csv_path)
            print(f"      コアCSV読み込み: {len(df)}行")
        except Exception as e:
            print(f"      コアCSV読み込みエラー: {e}")
            return None
        
        # アルゴリズム実行
        try:
            config = Config()
            detector = DrowsyDetector(config)
            detector.set_frame_rate(float(self.config['algorithm']['frame_rate']))
            
            algo_results = []
            for _, row in df.iterrows():
                input_data = InputData(
                    frame_num=int(row['frame']),
                    left_eye_open=float(row['leye_openness']),
                    right_eye_open=float(row['reye_openness']),
                    face_confidence=float(row['confidence'])
                )
                
                output = detector.update(input_data)
                algo_results.append({
                    'frame_num': output.frame_num,
                    'is_drowsy': int(output.is_drowsy),
                    'left_eye_closed': output.left_eye_closed,
                    'right_eye_closed': output.right_eye_closed,
                    'continuous_time': output.continuous_time,
                    'error_code': output.error_code or ''
                })
            
            print(f"      アルゴリズム実行完了: {len(algo_results)}フレーム")
            
        except Exception as e:
            print(f"      アルゴリズム実行エラー: {e}")
            return None
        
        # アルゴCSVの保存
        try:
            algo_df = pd.DataFrame(algo_results)
            algo_csv_path = self.run_output_dir / f"{video_id}.csv"
            algo_df.to_csv(algo_csv_path, index=False)
            print(f"      アルゴCSV保存: {algo_csv_path}")
        except Exception as e:
            print(f"      アルゴCSV保存エラー: {e}")
            return None
        
        # DataWareHouseに登録
        try:
            # database.dbを基準とした相対パスでDataWareHouseに登録
            db_dir = Path(self.db_path).parent.resolve()
            output_dir_relative = str(self.run_output_dir.resolve().relative_to(db_dir))
            algorithm_output_id = dwh.create_algorithm_output(
                algorithm_id=algorithm_id,
                core_lib_output_id=core_lib_output_id,
                output_dir=output_dir_relative,
                db_path=self.db_path
            )
            print(f"      DataWareHouse登録: algorithm_output_ID={algorithm_output_id}")
        except Exception as e:
            print(f"      DataWareHouse登録エラー: {e}")
            return None
        
        return {
            'video_id': video_id,
            'core_lib_output_id': core_lib_output_id,
            'algorithm_output_id': algorithm_output_id,
            'algo_csv_path': algo_csv_path,
            'algo_results': algo_results
        }
    
    def _run_evaluation_logic(self, algorithm_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """評価ロジックの実行"""
        print(f"[{self.run_id}] 評価ロジック実行中...")
        
        total_tasks = 0
        total_correct = 0
        per_video_results = []
        detailed_results = []  # マークダウン生成用の詳細結果
        
        for result in algorithm_results:
            video_id = result['video_id']
            algo_results = result['algo_results']
            
            print(f"    ビデオID={video_id} 評価中...")
            
            # タグ情報の取得
            try:
                tags = dwh.get_video_tags(video_id, db_path=self.db_path)
                print(f"      タグ数: {len(tags)}")
            except Exception as e:
                print(f"      タグ取得エラー: {e}")
                continue
            
            # ビデオごとの評価
            video_tasks = []
            video_correct = 0
            
            for tag in tags:
                task_id = f"{video_id}_{tag['tag_ID']}"
                start_frame = tag['start']
                end_frame = tag['end']
                
                # 区間内のis_drowsyを集計
                drowsy_frames = [
                    r for r in algo_results 
                    if start_frame <= r['frame_num'] <= end_frame and r['is_drowsy'] == 1
                ]
                
                predicted = 1 if len(drowsy_frames) > 0 else 0
                ground_truth = 1  # 仕様書に基づき、全タグ区間が「連続閉眼あり」
                correct = int(predicted == ground_truth)
                
                video_tasks.append({
                    'task_id': task_id,
                    'predicted': predicted,
                    'ground_truth': ground_truth,
                    'correct': correct,
                    'notes': f"frames {start_frame}-{end_frame}, drowsy_frames={len(drowsy_frames)}"
                })
                
                video_correct += correct
            
            # ビデオごとの結果保存
            if video_tasks:
                video_accuracy = video_correct / len(video_tasks)
                video_result = {
                    'video_id': video_id,
                    'accuracy': video_accuracy,
                    'num_correct': video_correct,
                    'num_tasks': len(video_tasks),
                    'result_file_path': f"{video_id}.csv"
                }
                per_video_results.append(video_result)
                
                # 詳細結果の保存
                tasks_df = pd.DataFrame(video_tasks)
                csv_path = self.evaluation_output_dir / f"{video_id}.csv"
                tasks_df.to_csv(csv_path, index=False)
                print(f"      評価結果保存: {csv_path}")
                print(f"      正解率: {video_accuracy:.3f} ({video_correct}/{len(video_tasks)})")
                
                # マークダウン生成用の詳細結果を追加
                detailed_results.append({
                    'video_id': video_id,
                    'algorithm_results': algo_results,
                    'evaluation_result': video_tasks
                })
                
                total_tasks += len(video_tasks)
                total_correct += video_correct
        
        # 全体サマリの作成
        overall_accuracy = total_correct / total_tasks if total_tasks > 0 else 0.0
        
        evaluation_summary = {
            'evaluation_summary': {
                'run_id': self.run_id,
                'created_at': datetime.now().isoformat(),
                'algorithm_version': self.algorithm_version,
                'algorithm_commit_hash': self.algorithm_commit_hash,
                'evaluation_conditions': {
                    'frame_rate': self.config['algorithm']['frame_rate'],
                    'ground_truth': 'all_tags_continuous_closed_eyes'
                },
                'overall_results': {
                    'accuracy': overall_accuracy,
                    'total_num_correct': total_correct,
                    'total_num_tasks': total_tasks
                },
                'per_dataset': per_video_results
            }
        }
        
        # サマリの保存
        summary_path = self.evaluation_output_dir / "evaluation_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_summary, f, ensure_ascii=False, indent=2)
        
        # マークダウンレポートの生成
        markdown_path = self._generate_markdown_report(evaluation_summary, detailed_results)
        
        print(f"    全体正解率: {overall_accuracy:.3f} ({total_correct}/{total_tasks})")
        print(f"    評価サマリ保存: {summary_path}")
        print(f"    マークダウンレポート保存: {markdown_path}")
        
        return evaluation_summary

    def _register_evaluation_to_db(self, algorithm_results: List[Dict[str, Any]], evaluation_summary: Dict[str, Any]) -> Dict[str, Any]:
        """評価結果をDataWareHouseに登録（集計＋明細）
        Returns: { 'evaluation_result_id': int or None, 'num_evaluation_data': int }
        """
        summary = evaluation_summary.get('evaluation_summary', {})
        overall = summary.get('overall_results', {})
        per_dataset = summary.get('per_dataset', [])

        if not self.algorithm_id:
            print(f"[{self.run_id}] 評価結果登録スキップ: algorithm_id 未確定")
            return { 'evaluation_result_id': None, 'num_evaluation_data': 0 }

        # 評価結果ディレクトリの相対パス化
        db_dir = Path(self.db_path).parent.resolve()
        try:
            eval_dir_relative = str(self.evaluation_output_dir.resolve().relative_to(db_dir))
        except Exception:
            # 既に相対の場合など
            eval_dir_relative = str(self.evaluation_output_dir)

        # 集計レコードの登録（false_positive は暫定 None）
        try:
            evaluation_result_id = dwh.create_evaluation_result(
                version=self.algorithm_version,
                algorithm_id=self.algorithm_id,
                true_positive=float(overall.get('accuracy', 0.0)),
                false_positive=None,
                evaluation_result_dir=eval_dir_relative,
                evaluation_timestamp=datetime.now().isoformat(),
                db_path=self.db_path,
            )
            print(f"[{self.run_id}] 評価集計登録: evaluation_result_ID={evaluation_result_id}")
        except Exception as e:
            print(f"[{self.run_id}] 評価集計登録エラー: {e}")
            return { 'evaluation_result_id': None, 'num_evaluation_data': 0 }

        # 動画ごとの明細登録のために、video_id -> (num_correct, num_tasks, result_file_path) を用意
        dataset_index = { d['video_id']: d for d in per_dataset }

        created_count = 0
        for result in algorithm_results:
            video_id = result['video_id']
            algorithm_output_id = result['algorithm_output_id']
            ds = dataset_index.get(video_id)
            if not ds:
                # 評価対象外（タグ無し等）の場合スキップ
                continue

            correct = int(ds.get('num_correct', 0))
            total = int(ds.get('num_tasks', 0))
            result_file = ds.get('result_file_path', f"{video_id}.csv")
            evaluation_data_path = str(Path(eval_dir_relative) / result_file)

            try:
                dwh.create_evaluation_data(
                    evaluation_result_id=evaluation_result_id,
                    algorithm_output_id=algorithm_output_id,
                    correct_task_num=correct,
                    total_task_num=total,
                    evaluation_data_path=evaluation_data_path,
                    db_path=self.db_path,
                )
                created_count += 1
            except Exception as e:
                print(f"[{self.run_id}] 評価明細登録エラー (video_ID={video_id}): {e}")

        print(f"[{self.run_id}] 評価明細登録完了: {created_count}件")
        return { 'evaluation_result_id': evaluation_result_id, 'num_evaluation_data': created_count }
    
    def _generate_markdown_report(self, evaluation_summary: Dict[str, Any], evaluation_results: List[Dict[str, Any]]) -> str:
        """マークダウン形式の評価レポートを生成"""
        from datetime import datetime
        
        summary = evaluation_summary['evaluation_summary']
        markdown_lines = []
        
        # ヘッダー
        markdown_lines.append("# drowsy_detection 評価レポート")
        markdown_lines.append("")
        markdown_lines.append(f"**実行日時**: {summary['created_at']}")
        markdown_lines.append(f"**実行ID**: `{summary['run_id']}`")
        markdown_lines.append(f"**アルゴリズムバージョン**: `{summary['algorithm_version']}`")
        markdown_lines.append(f"**コミットハッシュ**: `{summary['algorithm_commit_hash']}`")
        markdown_lines.append("")
        
        # 評価条件
        markdown_lines.append("## 📋 評価条件")
        markdown_lines.append("")
        conditions = summary['evaluation_conditions']
        markdown_lines.append(f"- **フレームレート**: {conditions['frame_rate']} fps")
        markdown_lines.append(f"- **グラウンドトゥルース**: {conditions['ground_truth']}")
        markdown_lines.append("")
        
        # 全体結果
        overall = summary['overall_results']
        accuracy_percent = overall['accuracy'] * 100
        markdown_lines.append("## 🎯 全体評価結果")
        markdown_lines.append("")
        markdown_lines.append(f"- **全体正解率**: **{accuracy_percent:.1f}%** ({overall['total_num_correct']}/{overall['total_num_tasks']})")
        
        # 正解率の評価コメント
        if accuracy_percent >= 100:
            status_emoji = "🟢"
            status_text = "OK"
        else:
            status_emoji = "🔴"
            status_text = "未検知あり"
        
        markdown_lines.append(f"- **評価**: {status_emoji} {status_text}")
        markdown_lines.append("")
        
        # ビデオ別結果テーブル
        markdown_lines.append("## 📊 ビデオ別評価結果")
        markdown_lines.append("")
        markdown_lines.append("| ビデオID | 正解率 | 正解数/総数 | ステータス | 詳細 |")
        markdown_lines.append("|---------|--------|------------|-----------|------|")
        
        for dataset in summary['per_dataset']:
            video_id = dataset['video_id']
            accuracy = dataset['accuracy'] * 100
            correct = dataset['num_correct']
            total = dataset['num_tasks']
            
            # ステータス決定
            if accuracy >= 80:
                status = "🟢 優秀"
            elif accuracy >= 60:
                status = "🟡 良好"
            elif accuracy >= 40:
                status = "🟠 要改善"
            else:
                status = "🔴 要改善"
            
            markdown_lines.append(f"| {video_id} | {accuracy:.1f}% | {correct}/{total} | {status} | [詳細](#ビデオ{video_id}の詳細結果) |")
        
        markdown_lines.append("")
        
        # アルゴリズム検出統計
        markdown_lines.append("## 🔍 アルゴリズム検出統計")
        markdown_lines.append("")
        markdown_lines.append("| ビデオID | 総フレーム数 | 検出フレーム数 | 検出率 | グラフ |")
        markdown_lines.append("|---------|-------------|---------------|--------|-------|")
        
        # 各ビデオの検出統計を取得
        for result in evaluation_results:
            video_id = result['video_id']
            algorithm_results = result['algorithm_results']
            total_frames = len(algorithm_results)
            drowsy_frames = sum(1 for r in algorithm_results if r['is_drowsy'])
            detection_rate = (drowsy_frames / total_frames) * 100 if total_frames > 0 else 0
            
            # 簡易グラフ（プログレスバー風）
            bar_length = 20
            filled_length = int(bar_length * (detection_rate / 100))
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            markdown_lines.append(f"| {video_id} | {total_frames:,} | {drowsy_frames:,} | {detection_rate:.2f}% | `{bar}` |")
        
        markdown_lines.append("")
        
        # 詳細結果セクション
        markdown_lines.append("## 📖 詳細結果")
        markdown_lines.append("")
        
        for result in evaluation_results:
            video_id = result['video_id']
            evaluation_result = result['evaluation_result']
            
            markdown_lines.append(f"### ビデオ{video_id}の詳細結果")
            markdown_lines.append("")
            
            # タグ別評価結果
            markdown_lines.append("| タスクID | アルゴリズム出力 | 真値 | 正解 | 詳細 |")
            markdown_lines.append("|----------|----------|------|------|------|")
            
            for eval_result in evaluation_result:
                task_id = eval_result['task_id']
                predicted = "✅ 検出" if eval_result['predicted'] else "❌ 未検出"
                ground_truth = "✅ 検出" if eval_result['ground_truth'] else "❌ 未検出"
                correct = "✅" if eval_result['correct'] else "❌"
                notes = eval_result.get('notes', '')
                
                markdown_lines.append(f"| {task_id} | {predicted} | {ground_truth} | {correct} | {notes} |")
            
            markdown_lines.append("")
        
        # フッター
        markdown_lines.append("---")
        markdown_lines.append("*このレポートは自動生成されました*")
        
        # ファイルに保存
        markdown_content = "\n".join(markdown_lines)
        markdown_path = self.evaluation_output_dir / "evaluation_report.md"
        
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(markdown_path)
    
    def _write_log(self, evaluation_results: Dict[str, Any], register_summary: Optional[Dict[str, Any]] = None):
        """ログファイルの更新"""
        log_file = self.config['logging']['file']
        
        overall = evaluation_results['evaluation_summary']['overall_results']
        log_entry = f"""
## 評価実行ログ - {self.run_id}

- **実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **対象件数**: {len(evaluation_results['evaluation_summary']['per_dataset'])}動画
- **全体正解率**: {overall['accuracy']:.3f} ({overall['total_num_correct']}/{overall['total_num_tasks']})
- **アルゴリズムバージョン**: {self.algorithm_version}
- **アルゴリズムハッシュ**: {self.algorithm_commit_hash}
- **出力先**: 
  - アルゴリズム出力: `{self.run_output_dir}`
  - 評価結果: `{self.evaluation_output_dir}`

"""

        # 評価結果DB登録サマリを追記（あれば）
        if register_summary and register_summary.get('evaluation_result_id') is not None:
            log_entry += (
                f"- **評価結果DB登録**: 明細 {register_summary.get('num_evaluation_data', 0)}件, "
                f"evaluation_result_ID={register_summary.get('evaluation_result_id')}\n\n"
            )
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print(f"[{self.run_id}] ログ更新: {log_file}")
        except Exception as e:
            print(f"[{self.run_id}] ログ更新エラー: {e}")


def main():
    """メイン関数"""
    print("drowsy_detection 評価エンジン")
    print("=" * 50)
    
    try:
        engine = EvaluationEngine()
        success = engine.run_evaluation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"評価エンジン初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
