# first-try

**あなたのコマンドラインツールは、説明書を読んでいない AI が初見で正しく使えますか？**

テストは、作者が知っている書き方でツールを呼びます。AI は一行の説明だけを読んで、「たぶんこう
いう名前だろう」と打ちます。`first-try` はその差を測り、外れた呼び方を一つずつ「二度と外れない
状態」にします。

AI 向けに作った 42 本のツールで最初に試したとき、**初見の呼び方 126 件のうち通ったのは 27 件**
でした。その 27 件のうち 1 件は、通ったのに結果が間違っていました。

## 入っているもの

| | |
|---|---|
| `first_try.py` | 4 つのコマンド。`brief`（何も知らない AI に見せる一覧）、`run`（AI が書いた呼び方を実行）、`edges`（全オプションに 0・-1・巨大な値を入れる）、`replay`（つまずきの台帳をテストとして再生） |
| `teach.py` | argparse に「打ち間違えたオプション名に、正しい名前を返す」機能を足す 20 行 |
| `skills/first-try-probe` | AI 向けの手順書: 別の AI に推測させる → 実行 → 読む → 教える → 記録 |
| `skills/edge-probe` | 値の手順書: 0・負の数・10 億を入れたらツールはどうなるか |
| `examples/ffmpeg-skill` | 元になった測定。126 件の推測と台帳つき |

Python 3.9 以上、標準ライブラリだけで動きます。スキルは普通の `SKILL.md` なので、2 つのフォルダ
をお使いのエージェントのスキル置き場（Claude Code なら `.claude/skills/`）にコピーしてください。

## 使い方

`tools.json` にツールを書きます（書式は `first_try.py` の先頭にあります）。

1. `python3 first_try.py brief tools.json > tools.txt`
2. `tools.txt` **だけ**を、何も知らない AI に渡します。ツールごとに現実的な依頼を 3 つ考えさせ、
   最初に打つ引数を JSON（`[{"tool", "request", "argv"}]`）で書かせます。
3. `python3 first_try.py run tools.json guesses.json`

| 行 | 意味 |
|---|---|
| `ran` | 通った。必ず読むこと。通ったのに間違っている場合があります |
| `taught` | 知らないオプションに対し、ツールが自分の正しいオプションを答えた |
| `silent` | 知らないオプションに対し、何も教えなかった |
| `refused` | それ以外の理由で断った |
| `hung` | 時間内に返事がなかった |

値を試すときは、最小限の正しい呼び方を `"base"` に書いて `python3 first_try.py edges tools.json`。

## 外れを直しっぱなしにしない

推測が外れるのは AI の不具合ではありません。3 つの AI が `--angle` と打ち、あなたのオプションが
`--degrees` なら、ツールがそう答えればよいのです。`teach.install(parser)` を足すと、知らない
オプションごとに「言葉を共有するオプション」「綴りの近いオプション」「説明文にその言葉が出てくる
オプション」を返します。なので、一番安い直し方は、説明文に言葉を一つ足すことです。

外れた呼び方は 1 行ずつ台帳（`stumbles.jsonl`）に書き、CI で
`python3 first_try.py replay tools.json stumbles.jsonl` を回します。教えたはずの呼び方に答えなく
なったら、終了コード 1 で落ちます。

## やらないこと

- 推測は書きません。書くのは「コードを知らない」別の AI です。同じ推測を次の測定に使い回すと、
  何も測れません。
- 行の良し悪しは判定しません。`ran` は合格ではなく、`refused` は失敗ではありません。人か AI が
  読んで決めます。
- `teach.py` は argparse 用です。考え方は、エラー処理を差し替えられるパーサーならどれでも使えます。

## 関連するもの

「何も知らないモデルに道具を使わせて、つまずきを見る」という考え方は新しくありません
（[Fresh Eyes as a Service](https://recursion.wtf/posts/llms_as_ux_testers/)、
[cli-agent-lint](https://github.com/Camil-H/cli-agent-lint)、
[AXI](https://github.com/kunchenguid/axi)）。端の値の手順は Trail of Bits の
[スキル](https://github.com/trailofbits/skills)（`sharp-edges`、`property-based-testing`）に
ならっています。

ここで足したのは、その先です。外れを「ツールが返す答え」に変え、テストが再生する台帳に残すので、
次に同じことを打った AI には正しい名前が返ります。

MIT ライセンス。[English](README.md)
