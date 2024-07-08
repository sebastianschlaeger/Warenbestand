import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sku = request.form['sku']
        price = float(request.form['price'])
        new_item = Item(sku=sku, price=price)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))
    
    items = Item.query.all()
    return render_template('index.html', items=items)

if __name__ == '__main__':
    app.run(debug=True)
