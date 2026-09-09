# エイリアンズ コードフォーム選択 PoC（v12）

iPhone Safari 実機で「コードカードをタップ → フォーム候補から選択 → 表示が即時変更 →
再読み込みしても選択が残る」を成立させるための最小PoC。

- 本体: `index.html`（外部依存なし・1ファイル完結）
- 生成元: `../tools/`（後述）

## 受入条件（CODEX_START_HERE.md より）

1. コードカードをタップ
2. 複数のコードフォーム候補が表示
3. 1つ選択
4. ダイアグラム／フォーム表示が即時変更
5. ページを再読み込み
6. 選択したフォームが保持されている

ページ上部に「iPhone Safari 受入テスト」パネルを常設し、①〜⑤の判定を画面上に表示する。
⑤が緑（OK）になり、保存したフォーム名が表示されれば合格。

## 検証状況

| 環境 | 実施 | 結果 |
|---|---|---|
| WebKitGTK 2.52（Safari と同一の WebKit エンジン）+ WebDriver、実HTTPサーバ経由 | 済 | 19/19 PASS |
| Chromium（iPhone 13 エミュレーション・実タップ・実HTTPサーバ経由） | 済 | 21/21 PASS |
| **iPhone Safari 実機** | **未** | **ユーザー確認待ち** |

WebKitGTK は Safari と同じ WebKit だが iOS Safari そのものではない。
**実機で①〜⑤を確認するまで「Safari対応済み」とは扱わない。**

## v9/v11 から直した実際の不具合

1. **ピンクの「次」コード `Baug7(b9)` にフォーム候補が無く、タップしても選べなかった**
   → 曲中で使う全38コード（`N.C.` を除く37コード）にフォームを登録。未登録はゼロ。
2. **ダイアグラムの押弦ドットが JS 再描画時に見えなかった**
   → `.dot` に width/height が無く 0×0 だった。CSS で実寸を指定。
3. **10フレット以上のフォームがダイアグラム化できなかった**（`x9A9A9` / `x8A898`）
   → ハイフン区切り表記（`x-9-11-9-10-9`）に対応するパーサへ変更。
4. **`F7 x8A898` は構成音が誤りだった**（2弦が G# になり、7th の A が出ない）
   → 全フォームを構成音で機械検証する仕組みに置き換え、誤ったフォームは採用しない。
5. **JSが落ちると画面が白いまま原因が分からなかった**
   → `window.onerror` を画面上のエラー枠に表示。譜面は静的HTMLとして事前描画。

## Safari 向けに入れた対策

- JS は ES5 相当で記述（アロー関数・テンプレートリテラル・オプショナルチェーン不使用）
- 背景タップで閉じる領域を `<div>` ではなく `<button>` に（iOS で div の click が拾われない件）
- `touch-action:manipulation` / `-webkit-tap-highlight-color`
- シート表示中の背景スクロール固定と復帰（`position:fixed` + スクロール位置復元）
- `-webkit-overflow-scrolling:touch`、`env(safe-area-inset-bottom)`
- localStorage はプライベートブラウズ等の例外を捕捉し、使えない場合はメモリへ退避したうえで
  「保存一時」と画面に明示する（黙って失敗しない）

## 未確定・未検証（推測で埋めていない項目）

- iPhone Safari 実機での動作（最重要・未実施）
- 複数コード小節の拍割りは v11 から引き継いだ暫定値
- 歌詞は著作権上プレースホルダーのみ
- フォーム選択の粒度は「コード名単位（曲全体で共通）」。
  「グローバル既定＋出現箇所別上書き」は未実装
- 音源との厳密な再生同期は未実施（BPM 85 固定の擬似カーソル）

## フォーム辞書の作り方（`../tools/`）

```
python3 tools/gen2.py       # 定番形＋探索 → 構成音を検証 → tools/voicings.json
python3 tools/build_app.py  # measures.json + voicings.json → aliens/index.html
```

`tools/gen_voicings.py` に各コードの構成音定義と検証ロジックがある。判定は以下の全てを満たすもののみ採用:

- 鳴る弦の音がすべてそのコードの構成音であること
- 必須音（ルート・3rd/sus・7th・指定テンション）がすべて含まれること
- オンコードは最低音が指定ベース音であること
- 押弦4本以内（セーハ考慮）、4フレット幅以内
- 鳴る弦が連続（6弦が鳴っているときの5弦ミュートのみ許可）

`定番形` = 人が与えた定番シェイプのうち検証を通ったもの、`探索` = 探索で見つけたもの。
どちらも構成音は機械検証済み。

## 自動テストの流し方

```
python3 -m http.server 8765 --bind 127.0.0.1 &
node tools/test_chromium.js http://127.0.0.1:8765/aliens/index.html   # Chromium(iPhone13)
Xvfb :99 -screen 0 400x900x24 & 
DISPLAY=:99 python3 tools/test_webkit.py http://127.0.0.1:8765/aliens/index.html  # WebKit
```

WebKit 側は `apt-get install webkit2gtk-driver xvfb` と `pip install selenium` が必要。
Chromium 側は Playwright が必要（`test_chromium.js` 冒頭の require パスを環境に合わせる）。
`file://` ではなく必ず HTTP 経由で開くこと（`about:blank` / `set_content` では
localStorage が永続せず、再読み込み保持の検証にならない。これは v11 のテストの限界だった点）。
