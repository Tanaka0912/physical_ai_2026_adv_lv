# UR3 Pick and Place + A* 配置先計画

最終課題サンプル「Pick and Place Task - ROS2 Gazebo Simulation (UR3 + Robotiq 2f-85)」を出発点にした、追加学習・外部AI API不要のローカル実装です。UR3 が円柱を把持し、A* で選んだ左右の配置先へ運びます。

## 構成と独自要素

- **ベース**: [UR3_ROS2_PICK_AND_PLACE](https://github.com/darshmenon/UR3_ROS2_PICK_AND_PLACE) のコミット `5e481d01492860dcef61992edfbe9f14ba98616d`（BSD-3-Clause）。UR3、Robotiq、Gazebo、MoveIt Task Constructor のシーンと動作を使用します。
- **AI**: [`planner/plan_place.py`](planner/plan_place.py) のA*が、アーム基部の占有領域を避けて円柱のピック位置から左右のビンへの到達可能性とXY経路長を評価し、配置先を選びます。選択結果をMTCパラメータに書き込みます。MoveItが関節軌道を計画・検証します。モデルの追加学習やAPIキーは使いません。
- **シミュレーション同期**: 元のサンプルはMoveIt内の衝突物体のみを手先に取り付けます。[`planner/sync_gazebo_object.py`](planner/sync_gazebo_object.py) はグリッパーの関節状態から把持・解放を判定し、Gazebo側の赤い円柱を手先へ追従させ、選択したビンの底へ配置します。Gazeboの円柱は衝突を持たない表示マーカーです。ロボットの経路に対する物体の衝突判定はMoveItが行います。

## 動作環境

- Windows 11 の WSL2、Ubuntu 24.04
- ROS 2 Jazzy、Gazebo Harmonic、MoveIt 2
- このPCではWSLメモリ約7.4 GiB、スワップ2 GiBでヘッドレス実行を確認

## セットアップ

Ubuntu 24.04 のWSL内でrootとして実行します。ROSリポジトリ追加、apt依存関係の導入、ベースリポジトリの取得、Jazzy互換修正、ビルドを行います。

```bash
cd ~/phsycal_ai
bash scripts/setup_wsl.sh
```

公開する際は、このリポジトリのコードとパッチに加え、上記ベースリポジトリの出典とライセンスを残してください。再現用の修正は [`scripts/patch_moveit_jazzy.py`](scripts/patch_moveit_jazzy.py)、[`scripts/patch_gazebo_marker.py`](scripts/patch_gazebo_marker.py) と `patches/` にあります。

## 実行と確認

```bash
cd ~/phsycal_ai
bash scripts/run_planned.sh
```

実行時に `generated/plan.json` と `generated/mtc_node_params.yaml` が作られます。`plan.json` の `selected_bin` と `route_xy` でA*の判断を確認できます。右ビンが使えない想定で左を選ばせる場合は `bash scripts/run_planned.sh --block right` です。左右どちらの実行も確認済みです。

スクリプトはMTCの実行とGazebo内の円柱位置を自動で検証し、成功なら終了コード0を返します。結果は `generated/verification.json`、詳細ログは `logs/baseline.log` と `logs/object_sync.log` に保存します。起動したGazeboは検証後に停止します。実行中に手動で再検証する場合は別のWSL端末で次を実行できます。

```bash
source /opt/ros/jazzy/setup.bash
python3 scripts/verify_result.py
```

長時間実行は10分で自動停止します。GUIは使わずに実行します。レポート、公開・提出は別作業です。

## デモ動画

提出仕様に合わせたMP4は [`output/PAI_pick_and_place_demo.mp4`](output/PAI_pick_and_place_demo.mp4) です。108.55秒、1280×720、20 fps、H.264、等速再生です。通常条件で右ビンを選ぶ実行と、右ビンを使用不可にした条件で左ビンへ切り替える実行を続けて示します。最後に両方のGazebo座標検証結果を表示します。映像には氏名やメールアドレスを入れていません。

再作成する場合は、WSL内で次の順に実行します。録画スクリプトは俯瞰カメラの向きを配置先ごとに切り替え、使っていない深度カメラを一時停止します。終了時に元のカメラ設定へ戻します。

```bash
cd ~/phsycal_ai
bash scripts/record_take.sh right
bash scripts/record_take.sh left --block right
python3 scripts/edit_demo_video.py
bash scripts/encode_demo_video.sh
python3 scripts/verify_demo_video.py
```

動画内の赤い円柱はMoveItの把持状態に合わせて移動するGazebo表示マーカーです。接触と摩擦による実際の把持を映したものではありません。

## 動作確認結果

2026-10-21、WSL2上で右ビンと、`--block right` による左ビンへの配置を確認しました。両方ともMTCが `Task executed successfully` を出力し、Gazeboの円柱中心は選択ビンの中心とXYで一致、高さはビン基準で0.07 mでした。左右の計画・検証結果は `generated/plan_left.json` / `generated/verification_left.json` と通常の `generated/plan.json` / `generated/verification.json` に保存しています。

## 制約

A*の格子は高水準の配置先選択用で、A*経路そのものをアームが追従するわけではありません。関節の衝突判定・到達性はMoveIt側が担当します。Gazebo物体の追従は物理的なグリップを再現しません。最終課題の動画・レポートではこの制約を明記してください。
