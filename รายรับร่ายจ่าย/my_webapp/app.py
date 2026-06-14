from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

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

    if selected_filter:
        records = Record.query.filter_by(category_name=selected_filter).order_by(Record.date.desc(), Record.id.desc()).all()
    else:
        records = Record.query.order_by(Record.date.desc(), Record.id.desc()).all()
        
    categories = Category.query.all() 
    
    total_income = sum(item.amount for item in records if item.type == 'รายรับ')
    total_expense = sum(item.amount for item in records if item.type == 'รายจ่าย')
    balance = total_income - total_expense
    
    return render_template('index.html', 
                           records=records, 
                           categories=categories,
                           total_income=total_income, 
                           total_expense=total_expense, 
                           balance=balance,
                           selected_filter=selected_filter)

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
    if cat_name:
        existing = Category.query.filter_by(name=cat_name).first()
        if not existing:
            new_cat = Category(name=cat_name)
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