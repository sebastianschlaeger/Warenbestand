import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)

# Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'  # Für Flash-Nachrichten

db = SQLAlchemy(app)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sku = request.form['sku']
        price = float(request.form['price'])
        existing_item = Item.query.filter_by(sku=sku).first()
        if existing_item:
            existing_item.price = price
        else:
            new_item = Item(sku=sku, price=price)
            db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))
    
    items = Item.query.all()
    total_value = sum(item.price * item.quantity for item in items)
    return render_template('index.html', items=items, total_value=total_value)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Keine Datei ausgewählt')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('Keine Datei ausgewählt')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        process_excel(file_path)
        os.remove(file_path)  # Datei nach Verarbeitung löschen
        flash('Datei erfolgreich verarbeitet')
    else:
        flash('Nicht erlaubter Dateityp')
    return redirect(url_for('index'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def process_excel(file_path):
    df = pd.read_excel(file_path)
    for _, row in df.iterrows():
        sku = str(row['SKU'])[:5]  # Nur die ersten 5 Ziffern der SKU
        quantity = row['Menge']
        
        item = Item.query.filter_by(sku=sku).first()
        if item:
            item.quantity = quantity
        else:
            flash(f'SKU {sku} nicht in der Datenbank gefunden')
    db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    app.run(debug=True)
