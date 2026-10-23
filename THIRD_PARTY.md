# SO-101モデルの出典

- 配布元：TheRobotStudio / SO-ARM100
- リポジトリ：https://github.com/TheRobotStudio/SO-ARM100
- 使用モデル：`Simulation/SO101/so101_new_calib.urdf`（SO-101 follower）と、このURDFが参照する13個のSTL。
- 固定コミット：`a758567c3978dfeefe282ede0500085a48fe8f78`
- ライセンス：Apache License 2.0。原文は `assets/so101/LICENSE` に同梱。
- 元の説明：`assets/so101/UPSTREAM_README.md` に同梱。
- 出典とSHA-256：`assets/so101/source_manifest.json` に記録。

元のURDFとSTLは変更していません。`prepare_model.py` が元のURDFから生成する
`so101_press_probe.urdf` だけに、固定ジョイントで25mmの押下用先端と直径18mmの接触球を追加しています。
生成URDFの冒頭にも変更を明記しています。SO-101の関節位置・可動範囲・慣性・メッシュは元の定義です。
グリッパーは閉じた状態を保ち、追加先端でボタンを押します。

本課題のカメラ認識・ボタン台・タスク・制御・動画・レポートは独自の実装です。
講座サンプルのコードは転載していません。公式モデルの使用とサンプルの丸写しは区別して説明しています。
