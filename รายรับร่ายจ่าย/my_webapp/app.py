from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    budget = db.Column(db.Float, default=0.0) # เพิ่มช่องเก็บงบประมาณ

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False) 
    category_name = db.Column(db.String(50), nullable=False, default="ทั่วไป") 
    amount = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()
    if not Category.query.first():
        default_categories = ['อาหาร/เครื่องดื่ม', 'เดินทาง', 'ที่อยู่อาศัย', 'เงินเดือน', 'ทั่วไป']
        for cat_name in default_categories:
            db.session.add(Category(name=cat_name))
        db.session.commit()

@app.route('/')
def index():
    selected_filter = request.args.get('filter')
    search_query = request.args.get('search')
    
    query = Record.query

    if selected_filter:
        query = query.filter_by(category_name=selected_filter)
        
    if search_query:
        query = query.filter(Record.name.like(f'%{search_query}%'))
        
    records = query.order_by(Record.date.desc(), Record.id.desc()).all()
    categories = Category.query.all() 
    
    total_income = sum(item.amount for item in records if item.type == 'รายรับ')
    total_expense = sum(item.amount for item in records if item.type == 'รายจ่าย')
    balance = total_income - total_expense

    # คำนวณงบประมาณ
    all_records = Record.query.all()
    expense_by_cat = {}
    for item in all_records:
        if item.type == 'รายจ่าย':
            expense_by_cat[item.category_name] = expense_by_cat.get(item.category_name, 0) + item.amount

    budget_status = []
    for cat in categories:
        if cat.budget > 0:
            spent = expense_by_cat.get(cat.name, 0)
            percent = (spent / cat.budget) * 100 if cat.budget > 0 else 0
            budget_status.append({
                'name': cat.name,
                'budget': cat.budget,
                'spent': spent,
                'percent': round(percent, 2)
            })
    
    return render_template('index.html', 
                           records=records, 
                           categories=categories,
                           total_income=total_income, 
                           total_expense=total_expense, 
                           balance=balance,
                           selected_filter=selected_filter,
                           search_query=search_query,
                           budget_status=budget_status)

@app.route('/graph')
def graph():
    all_records = Record.query.all()
    total_income = sum(item.amount for item in all_records if item.type == 'รายรับ')
    total_expense = sum(item.amount for item in all_records if item.type == 'รายจ่าย')
    
    expense_by_cat = {}
    for item in all_records:
        if item.type == 'รายจ่าย':
            expense_by_cat[item.category_name] = expense_by_cat.get(item.category_name, 0) + item.amount
            
    chart_labels = list(expense_by_cat.keys())
    chart_values = list(expense_by_cat.values())
    
    return render_template('graph.html', total_income=total_income, total_expense=total_expense, chart_labels=chart_labels, chart_values=chart_values)

@app.route('/export')
def export_csv():
    records = Record.query.order_by(Record.date.desc(), Record.id.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['วันที่', 'ชื่อรายการ', 'หมวดหมู่', 'ประเภท', 'จำนวนเงิน (บาท)'])
    for item in records:
        cw.writerow([item.date.strftime('%d/%m/%Y'), item.name, item.category_name, item.type, item.amount])
    output = si.getvalue()
    response = Response('\ufeff' + output, mimetype='text/csv', content_type='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename=expense.csv'
    return response

@app.route('/add', methods=['POST'])
def add_item():
    date_str = request.form.get('date') 
    name = request.form.get('name')
    item_type = request.form.get('type')
    category_name = request.form.get('category') 
    try:
        record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount = float(request.form.get('amount'))
        if amount > 0:
            new_record = Record(date=record_date, name=name, type=item_type, amount=amount, category_name=category_name)
            db.session.add(new_record)
            db.session.commit()
    except ValueError:
        pass 
    return redirect(url_for('index'))

@app.route('/add_category', methods=['POST'])
def add_category():
    cat_name = request.form.get('category_name').strip()
    budget_str = request.form.get('budget', '0')
    try:
        budget = float(budget_str) if budget_str else 0.0
    except ValueError:
        budget = 0.0

    if cat_name:
        existing = Category.query.filter_by(name=cat_name).first()
        if not existing:
            new_cat = Category(name=cat_name, budget=budget)
            db.session.add(new_cat)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_category/<int:id>')
def delete_category(id):
    cat = Category.query.get_or_404(id)
    try:
        db.session.delete(cat)
        db.session.commit()
    except:
        pass
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_item(id):
    record_to_delete = Record.query.get_or_404(id)
    try:
        db.session.delete(record_to_delete)
        db.session.commit()
    except:
        pass
    return redirect(request.referrer or url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)