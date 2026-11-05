# listen-read

TOEIC 用の聞き読みアプリ。GitHub Pages で公開: https://kouhalove32-boop.github.io/listen-read/

- `index.html` … アプリ本体（ホーム画面に追加して使う）
- `data/problems.json` … 問題データ（ここを更新すると音声が自動で作られる）
- `tools/gen_audio.py` … Kokoro で音声（mp3）と単語の時刻（json）を作るスクリプト
- `.github/workflows/audio.yml` … 10声分の音声を GitHub Actions で作ってコミットする
- `audio/<voice>/<id>.mp3|json` … 生成された音声
- `bench.html` … iPhone 内で Kokoro を動かす速度テスト（参考）

## ライセンス
- ソースコード：[MIT](LICENSE)
- 利用しているもの（Kokoro-82M、フォントなど）：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

TOEIC は ETS の登録商標です。このアプリは ETS および IIBC とは関係のない非公式アプリで、収録している教材はすべてオリジナルです。
