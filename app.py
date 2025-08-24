import sqlite3
import datetime
import csv
from urllib.parse import quote
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, session, Response, Blueprint

# 1. Blueprintを作成し、URLプレフィックスを設定
kakeibo_bp = Blueprint('kakeibo', __name__, url_prefix='/kakeibo')
DATABASE = 'database.db'

# 2. テンプレートフィルタをBlueprintに紐付け
@kakeibo_bp.app_template_filter('format_currency')
def format_currency(value):
    if value is None: return ""
    return "{:,}".format(value)

def get_db():
    conn = sqlite3.connect(DATABASE); conn.row_factory = sqlite3.Row; return conn

def close_connection(exception):
    # gオブジェクトはappコンテキストに依存するためここでは使わない
    pass

REGULAR_CATEGORIES = ["旅費交通費", "通信費", "広告宣伝費", "接待交際費", "消耗品費", "車両費", "損害保険料", "修繕費", "研究費", "雑費", "地代家賃", "水道光熱費", "事業主費"]
PROPRIETOR_CATEGORIES = ["住宅費", "食費", "外食", "日用品", "美容費", "水道光熱費", "通信料", "保険料", "医療費", "車両費", "保育料/学費", "税金", "習い事", "交通費", "被服費", "趣味費", "サブスク費", "その他"]

# 3. すべてのルートをBlueprintに紐付け
@kakeibo_bp.route('/')
def index():
    sort_order = request.args.get('sort_order', 'desc')
    if sort_order not in ['asc', 'desc']: sort_order = 'desc'
    conn = get_db()
    query = f'SELECT * FROM expenses ORDER BY date {sort_order}, id {sort_order}'
    expenses = conn.execute(query).fetchall()
    conn.close()
    last_date = session.get('last_date', datetime.date.today().isoformat())
    return render_template('index.html', expenses=expenses, regular_categories=REGULAR_CATEGORIES, proprietor_categories=PROPRIETOR_CATEGORIES, last_date=last_date, current_sort_order=sort_order)

@kakeibo_bp.route('/add', methods=['POST'])
def add_expense():
    date = request.form['date_hidden']; amount = request.form['amount']; item_name = request.form['item_name']; category = request.form['category']
    sub_category = None
    proprietor_choice = request.form.get('proprietor_category')
    if proprietor_choice and proprietor_choice != "": category = "事業主費"; sub_category = proprietor_choice
    conn = get_db()
    conn.execute('INSERT INTO expenses (date, amount, item_name, category, sub_category) VALUES (?, ?, ?, ?, ?)',(date, amount, item_name, category, sub_category))
    conn.commit(); conn.close()
    session['last_date'] = date
    return redirect(url_for('kakeibo.index')) # Blueprint名を指定

def build_search_query_and_params():
    query = "SELECT * FROM expenses WHERE 1=1"
    params = {}
    if request.args.get('start_date'):
        query += " AND date >= :start_date"; params['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        query += " AND date <= :end_date"; params['end_date'] = request.args.get('end_date')
    if request.args.get('min_amount'):
        query += " AND amount >= :min_amount"; params['min_amount'] = int(request.args.get('min_amount'))
    if request.args.get('max_amount'):
        query += " AND amount <= :max_amount"; params['max_amount'] = int(request.args.get('max_amount'))
    if request.args.get('keyword'):
        query += " AND item_name LIKE :keyword"; params['keyword'] = f"%{request.args.get('keyword')}%"
    selected_categories = request.args.getlist('categories')
    if selected_categories:
        cat_placeholders = ', '.join([f':cat{i}' for i in range(len(selected_categories))])
        query += f" AND category IN ({cat_placeholders})"
        for i, cat in enumerate(selected_categories): params[f'cat{i}'] = cat
    selected_sub_categories = request.args.getlist('sub_categories')
    if selected_sub_categories:
        sub_cat_placeholders = ', '.join([f':subcat{i}' for i in range(len(selected_sub_categories))])
        query += f" AND sub_category IN ({sub_cat_placeholders})"
        for i, sub_cat in enumerate(selected_sub_categories): params[f'subcat{i}'] = sub_cat
    query += " ORDER BY date DESC"
    return query, params

@kakeibo_bp.route('/search')
def search():
    query, params = build_search_query_and_params()
    conn = get_db()
    results = conn.execute(query, params).fetchall()
    total_amount = sum(row['amount'] for row in results)
    conn.close()
    return render_template('search.html', all_categories=REGULAR_CATEGORIES, proprietor_categories=PROPRIETOR_CATEGORIES, results=results, total_amount=total_amount)

@kakeibo_bp.route('/export_csv')
def export_csv():
    query, params = build_search_query_and_params()
    conn = get_db()
    results = conn.execute(query, params).fetchall()
    conn.close()
    si = StringIO(); cw = csv.writer(si)
    cw.writerow(['日付', '品物', '勘定科目', '事業主費(内訳)', '金額'])
    for row in results: cw.writerow([row['date'], row['item_name'], row['category'], row['sub_category'] or '', row['amount']])
    output = si.getvalue()
    filename = quote("kakeibo_export.csv")
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename*=UTF-8''{filename}"})

# 4. Flaskアプリを作成し、Blueprintを登録する
def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_kakeibo_secret_key'
    app.register_blueprint(kakeibo_bp)
    # データベースの後片付け処理を登録
    app.teardown_appcontext(close_connection)
    return app

app = create_app()