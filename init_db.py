import sqlite3

DATABASE = 'database.db'

# 既存のデータベースファイルがあれば削除する
import os
if os.path.exists(DATABASE):
    os.remove(DATABASE)

# データベースに接続
conn = sqlite3.connect(DATABASE)
c = conn.cursor()

# expensesテーブルを作成
c.execute('''
    CREATE TABLE expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        sub_category TEXT
    )
''')

# 変更を確定
conn.commit()

# 接続を閉じる
conn.close()

print(f"データベース '{DATABASE}' を新しく初期化しました。")