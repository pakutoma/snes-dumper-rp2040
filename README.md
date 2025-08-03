# snes-dumper-rp2040
##  概要
RP2040マイコンを使ったスーパーファミコンのROM吸い出し機の実験的実装です。
MicroPythonで書かれており、PIOやDMAによって吸い出しの高速化を図っています。
吸い出し速度は200KB/sほどです。

## ハードウェアのパーツ
- メイン基板（/board のKiCadプロジェクト）
  - PCBプロトタイプ業者（JLCPCB等）に発注してください
- RP2040マイコンボードキット（秋月電子通商）
- 74HC273 * 3
- 2.5mmピッチ62ピンソケット（SNES用）
  - Aliexpressとかで買うといいです

## 使い方
1. ボードにclientの中身を書き込む
2. host.pyを実行する
3. 数分で吸い出される（失敗なら端子を掃除すると良い）

## 対応ROM
- LoROM
- HiROM
- ExHiROM

## 非対応ROM
- SA-1
- その他、動かないもの

## 参考にしたもの
- [SNES Development Wiki](https://snes.nesdev.org/wiki/Main_Page)
  - [Cartridge connector](https://snes.nesdev.org/wiki/Cartridge_connector)
  - [Memory map](https://snes.nesdev.org/wiki/Memory_map)
  - [ROM header](https://snes.nesdev.org/wiki/ROM_header)

## ライセンス
Apache License 2.0