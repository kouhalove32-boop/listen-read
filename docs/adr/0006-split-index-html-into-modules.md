# ADR-0006: index.html をビルドなしの ES Modules に分割する

- 状態: 採用（2026-11-05、段階的に実施。第一歩は #1 の `src/parser.js`）
- 日付: 2026-11-05

## 背景
`index.html` 1 ファイル（約 1100 行）に、画面・パーサー・再生エンジン・保存がすべて入っている。公開を前提に機能を足していくと、変更の影響範囲が読めず、テストも書けない。

## 決定（案）
ビルド工程を持たないまま、`<script type="module">` で役割ごとのファイルに分ける。

```
src/
  parser.js        // parse()：テスト対象。Python 側と同じテストデータを使う
  engine/kokoro.js // 事前生成音声の再生
  engine/device.js // speechSynthesis
  highlight.js
  store.js         // localStorage のキーとスキーマのバージョン管理
  views/*.js       // reader, probs, test, result, lib, add
  desktop.js       // window.desktop との橋渡し
```

テストは Node の標準テストランナー（`node --test`）で、`parser.js` などの純粋な関数から書く。

## 検討した選択肢
| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| **ビルドなし ES Modules** | 今の配信方法（Pages と `app://`）のまま。依存が増えない | 型がない。ファイル数のぶん、初回の読み込みが少し増える |
| Vite＋TypeScript | 型、HMR、本格的な構成 | ビルド工程が増え、Actions と Electron 側の手順も変わる |
| 現状維持 | 手間ゼロ | 負債が増え続ける |

## 結果（見込み）
- ＋ パーサーを Python 側と同じデータでテストできる（T2・T3 の解消）
- − 一度に分割すると壊れやすい → パーサー → 保存 → エンジン → 画面の順に、少しずつ切り出す
- 型が欲しくなったら JSDoc ＋ `// @ts-check` を足す（ビルド不要のまま）
