# ADR-0004: Windows 版は Electron で Web アプリを包む

- 状態: 採用
- 日付: 2026-11（後追いで記録）

## 背景
Windows で単体の .exe として使いたい。Web 版と機能をそろえたい。

## 決定
Electron で `index.html` と音声を同梱し、`app://` プロトコルで配信する。Windows 固有の機能（タスクバーのボタンと進捗、ズーム、ウィンドウ状態の保存）は `preload.js` の `window.desktop` 経由で Web 側に提供する。

## 検討した選択肢
| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| **Electron** | Chromium が同梱で挙動が確実。情報が多い | サイズが大きい（約 300MB）。speechSynthesis が Windows の声を拾えないことがある |
| Tauri | 小さい | Rust のツールチェーンが必要。WebView2 の音声の挙動差 |
| PWA を Edge でインストール | 追加の実装が不要 | 「.exe が欲しい」という要件に合わない |

## 結果
- ＋ Web 側の 1 つのコードで両方を提供できる
- − サイズ。端末の声の問題（T4）は SAPI 経由の合成などで個別に対応が必要
