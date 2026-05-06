# Java To Python for Spring (Cursor Prompt)

Java（Spring Boot）コードをPython（FastAPI）へ変換するための
**Cursor用プロンプトテンプレート**です。

---

## 🎯 概要

本プロンプトは、Spring Bootで構築されたバックエンドコードを
FastAPIベースのPythonコードへ変換することを目的としています。

単なる構文変換ではなく、以下を重視しています：

* Spring構造の再現
* Pythonicな設計
* 実行可能なAPIコードの生成

---

## ✨ 特徴

* Controller → FastAPI Router に変換
* DTO → Pydanticモデル化
* Service層のロジック分離
* DI（依存性注入）をFastAPI方式に変換
* 最低限のDB構造（SQLAlchemy）を再現
* 実際に動作するAPIコードを生成

---

## 🛠️ 使い方

1. Cursorを開く
2. 本リポジトリのプロンプトをコピー
3. Java（Spring）コードを貼り付け
4. 実行してPythonコードを生成

---

## 🔄 変換対象

以下のSpring構造に対応：

* `@RestController`
* `@Service`
* `@Repository`
* `@RequestMapping / @GetMapping / @PostMapping`
* `@RequestBody / @PathVariable / @RequestParam`
* DTO / Entity クラス

---

## 🚀 出力仕様

* FastAPIアプリとして実行可能なPythonコード
* 型ヒント付き
* 必要なimportを含む
* 1ファイル構成（シンプル設計）

---

## ⚠️ 制約

* Spring Security は未対応（簡略化されます）
* 複雑なJPAリレーションは簡略化されます
* AOP（Aspect）は変換されません
* 完全なコード変換ではなく、補助ツールです

---

## 🧠 設計思想

Java（Spring）とPython（FastAPI）は設計思想が大きく異なるため、
完全な自動変換は現実的ではありません。

そのため本プロンプトは：

> 「動作する叩き台を高速生成する」

ことにフォーカスしています。

---

## ⚙️ 実行方法（CLI連携）

以下のようなCLIツールと組み合わせて使用できます：

```bash
JavaToPython Arg1(変換前Javaファイル) Arg2(変換後Pythonファイル)
```

---

## 🔮 今後の拡張

* LLM APIとの自動連携
* マルチファイル構成への対応
* Spring Securityの部分対応
* 非同期処理（async/await）の強化
* DBマイグレーション対応

---

## 📄 ライセンス

MIT License

---

## 👤 Author

* Koki Yoshimoto

---

## 💬 補足

このプロンプトは「完全変換」を目的としたものではなく、
**開発効率を上げるための生成テンプレート**です。


このツールは「完全変換」を目指すものではなく、
**移植作業のスタート地点を作るためのツール**です。

♯♯　実行例
python JavaToPython.py examples/Sample.java output.py
