# Genesis：AI色認識でSO-101が検査ボタンを操作

Physical AI 応用1講座の最終課題です。**講義で挙げられたGenesisを実際に使います。**
公式SO-101 followerモデルをGenesisに読み込み、カメラ画像をAIで分類して、
赤・緑・青のボタンを指示順に押します。実機なし、初級〜中級の内容です。

提出要件は **最終課題（10/19改訂版）** に基づきます。
OmniCampusアカウント名：**shirakashi**。YouTubeタイトル：**PAI最終課題_shirakashi**（限定公開）。

## 使用ツール

| 用途 | 実際の使用ツール |
|---|---|
| ロボット物理・関節PD制御・接触 | **Genesis 0.3.3、GPUバックエンド** |
| 仮想カメラ | **Genesis Rasterizer、EGL** |
| 実行環境 | Windows 11 / WSL2 Ubuntu 22.04 / Python 3.10 |
| GPU | NVIDIA RTX A2000 12GB、CUDA対応PyTorch |
| AI | scikit-learnのロジスティック回帰（色分類） |
| 逆運動学 | NumPy / SciPy、公式URDFの関節構造から数値計算 |
| 動画・PDF | Pillow / imageio / FFmpeg / ReportLab |

講義のGenesisで物理計算とカメラ描画を行う構成です。

## 成果物

- `outputs/demo.mp4`：実際のGenesis物理シミュレーションの動画。72秒、720p、20fps、1倍速。
- `説明資料_PAI最終課題_shirakashi.pdf`：概要、AIの担当、実測結果、前提・限界。
- `submission.zip`：コード・モデルとライセンス・動画・PDF・結果一式。
- `outputs/run_summary.json`：Genesisバージョン、GPU、認識・押下・関節角度などの実測記録。
- `outputs/verification.json`：動作、Genesisの使用、動画、モデル等の検証結果。
- `THIRD_PARTY.md`：公式SO-101の出典・ライセンス・変更内容。
- `YouTubeタイトル.txt`・`YouTube概要欄.txt`：アップロード時に貼り付ける文章。

## このPCで再実行する

`record_demo.bat` をダブルクリックすると、WSL2の専用環境を使って再録画します。
完成した動画は `outputs/replay/demo.mp4` です。提出用動画を上書きしません。

WSLのUbuntuターミナルで実行する場合：

```bash
cd /mnt/c/work-PhysicalAI/応用1/応用1_最終課題/genesis_ai_buttons
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}
${HOME}/physicalai-genesis-final/.venv/bin/python run_demo.py --record --output outputs/replay
```

録画なしの動作確認：

```bash
${HOME}/physicalai-genesis-final/.venv/bin/python run_demo.py --output outputs/check_run
${HOME}/physicalai-genesis-final/.venv/bin/python run_demo.py --colors blue,red,green --output outputs/check_alternate
```

物理計算はGPUで行います。最初の実行時はGenesisのカーネルコンパイルに時間がかかります。
通常の実行ではウィンドウを開かず、EGLでカメラを描画します。
動画の1秒はシミュレーション時間の1秒に対応し、録画処理の実時間とは異なります。

## タスクとAI

1. 固定俯瞰カメラでGenesisの実際の描画画像を取得する。
2. 既知のボタン位置に対応する6×6画素から平均RGBを取得し、明るさを正規化する。
3. 学習済みのロジスティック回帰で青・赤・緑を分類する。
4. AIの色認識結果を使い、色の指示を押すボタンの座標に変換する。
5. 可動範囲付き逆運動学で目標関節角を計算する。
6. Genesisの関節PD制御でアームを移動させ、ボタンを押す。
7. **先端との物理接触と4mm以上の沈み込み**を同時に確認して成功とする。
8. 先端を離し、待機位置へ戻る。

人工RGBデータ3,600件で学習し、別の乱数種による900件で評価します。
学習済みJSONモデルと学習コードを同梱。外部AI API・有料サービスは不要です。
AIは色認識を担当し、アームの制御は通常の数値計算です。
初期配置後、アームはPDモーター制御だけで動き、ボタンの位置をコードで直接書き換えません。
右側のカメラ欄は開始時の認識画像を保持します。

## 環境の再構築

このPCでは、既存のWSL Python 3.10用CUDA対応PyTorchを読み取り利用するため、
仮想環境に `--system-site-packages` を付けています。実行環境はUbuntu側の
`~/physicalai-genesis-final/.venv` に置き、コードと提出物はWindows側の本フォルダーに保存します。

```bash
python3 -m venv --system-site-packages "${HOME}/physicalai-genesis-final/.venv"
${HOME}/physicalai-genesis-final/.venv/bin/python -m pip install -r requirements.txt
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}
${HOME}/physicalai-genesis-final/.venv/bin/python check_genesis.py
```

他のPCで独立した環境を作る場合は、Linux / Python 3.10とNVIDIA GPUを用意し、
まずCUDA対応PyTorchをインストールしてからGenesis等を入れます。
このPCのPyTorchバージョンは実行記録に記載されています。
`requirements.txt` は主要ライブラリを固定し、`requirements-lock.txt` は専用環境へ
インストールしたパッケージを記録しています。既存環境から利用したPyTorch等の版は
`environment_versions.json` に記録しています。

```bash
python3 -m venv "${HOME}/physicalai-genesis-final/.venv"
${HOME}/physicalai-genesis-final/.venv/bin/python -m pip install 'torch==2.6.0' --index-url https://download.pytorch.org/whl/cu118
${HOME}/physicalai-genesis-final/.venv/bin/python -m pip install -r requirements.txt
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}
${HOME}/physicalai-genesis-final/.venv/bin/python check_genesis.py
```

日本語字幕・PDFはWindowsの日本語フォントを `/mnt/c/Windows/Fonts/` から読みます。
他の環境では `video_ui.py` と `build_report.py` の日本語フォントを変更してください。
EGL/OpenGLの描画ライブラリはWSLの既存環境を使用します。
WSLでは `export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}` を設定してから実行します。
GPUが利用できない場合、課題コードはCPUでの実行へ自動切替せずエラーを表示します。
モデルは同梱済みなので、通常の実行にネット接続は不要です。

## PDF・検証・ZIP

```bash
${HOME}/physicalai-genesis-final/.venv/bin/python build_report.py --account shirakashi
${HOME}/physicalai-genesis-final/.venv/bin/python verify_project.py --account shirakashi
${HOME}/physicalai-genesis-final/.venv/bin/python package_project.py --account shirakashi
```

## 前提と限界

- ボタン位置と大きさは既知。画像の既知位置を読む構成で、物体検出は未実装。
- 色認識の学習は人工RGBデータ。実環境の認識精度は未評価。
- 公式SO-101の5軸・グリッパーを利用。グリッパーは閉じ、25mmの固定押下用先端を追加。
- SO-101の可動範囲に合わせ、ボタンを低い・近い位置に置く。
- 関節角度・接触力・押下量はGenesisの値を使う。実機の調整・力センサー・安全性は未検証。
- 自己衝突の詳細な検証は行っていない。今回のタスクは物の把持・運搬を含まない。

##　実行方法
一番簡単なのは、フォルダー内の **[record_demo.bat](record_demo.bat) をダブルクリック**する方法です。
PowerShellから起動する場合は、次を実行してください。
```powershell
cd "C:\work-PhysicalAI\応用1\応用1_最終課題\genesis_ai_buttons"
.\record_demo.bat
```
この方法では、画面を表示せずにシミュレーションを録画します。完了後は、次の動画を開いて確認できます。
```text
outputs\replay\demo.mp4
```
**シミュレーションの画面を表示したい場合**は、同じフォルダーで次を実行します。WSLのGUI表示機能が必要です。
```powershell
wsl.exe -d Ubuntu-22.04 -- bash ./run_wsl.sh --gui --output outputs/gui_check
```
実行には、WSL2のUbuntu 22.04、NVIDIA GPU、セットアップ済みの専用Python環境が必要です。初回はGenesisのコンパイルに時間がかかります。
同梱動画の実行結果は `outputs/run_summary.json`、動画と物理押下の検証結果は `outputs/verification.json` に記録しています。

## ファイル

| ファイル | 内容 |
|---|---|
| `run_demo.py` | Genesisの物理環境・PD制御・カメラ・AI対象選択・動画 |
| `arm_control.py` | URDFから計算する可動範囲付き逆運動学 |
| `color_ai.py` | 色分類AIの学習・推論 |
| `scene_assets.py` | 上下に動く検査ボタン台 |
| `video_ui.py` | 実際のGenesis映像への日本語説明 |
| `prepare_model.py` | 公式SO-101からプローブ付きモデルを生成 |
| `fetch_so101.py` | 固定コミットからモデルを再取得 |
| `check_genesis.py` | GPU物理・EGLカメラの環境確認 |
| `build_report.py` | 実測結果から日本語PDF |
| `verify_project.py` | 動作・Genesis使用・動画全フレーム等を検証 |
| `package_project.py` | 提出物ZIP |
| `record_demo.bat` | WindowsからWSLで再録画 |
| `run_wsl.sh` | WSLのGPU設定を付けて実行するラッパー |

## 参考

- 最終課題（10/19改訂版）の使用ツール・AI・提出要件。
- Genesis 0.3.3：https://github.com/Genesis-Embodied-AI/Genesis/tree/v0.3.3
- Genesis公式説明：https://genesis-world.readthedocs.io/
- 公式SO-101：https://github.com/TheRobotStudio/SO-ARM100 （Apache-2.0）。
- 講座サンプル「SO-101入門」：https://note.com/npaka/n/nfaa9db0834e5 （題材の参考）。

本課題のボタン台・カメラAI・制御タスク・動画・レポートは独自実装です。
講義サンプルコードは転載していません。
