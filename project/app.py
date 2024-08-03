from flask import Flask, render_template, url_for, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

# Конфигурация приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Client')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}', '{self.role}')"

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.String(200), nullable=False)
    delivery_time = db.Column(db.String(100), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    delivery_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    client = db.relationship('User', foreign_keys=[client_id], backref='client_orders')
    delivery = db.relationship('User', foreign_keys=[delivery_id], backref='delivery_orders')

    def __repr__(self):
        return f"Order('{self.product_name}', '{self.client_name}', '{self.status}')"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Формы
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Электронная почта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Роль', choices=[('Client', 'Клиент'), ('Manager', 'Менеджер'), ('Delivery', 'Доставщик')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот адрес электронной почты уже занят. Пожалуйста, выберите другой.')

class LoginForm(FlaskForm):
    email = StringField('Электронная почта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class UpdateAccountForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Электронная почта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Обновить')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Этот адрес электронной почты уже занят. Пожалуйста, выберите другой.')

class OrderForm(FlaskForm):
    product_name = StringField('Название продукта', validators=[DataRequired()])
    client_name = StringField('ФИО клиента', validators=[DataRequired()])
    client_phone = StringField('Телефон клиента', validators=[DataRequired()])
    delivery_address = TextAreaField('Адрес доставки', validators=[DataRequired()])
    delivery_time = StringField('Время доставки', validators=[DataRequired()])
    payment_method = SelectField('Способ оплаты', choices=[('Card', 'Карта'), ('Cash', 'Наличные')])
    submit = SubmitField('Оформить заказ')

class OrderStatusForm(FlaskForm):
    status = SelectField('Статус', choices=[('Pending', 'В ожидании'), ('In Process', 'В обработке'), ('Canceled', 'Отменён'), ('Delivery Agreed', 'Доставка согласована'), ('In Delivery to Store', 'В доставке в магазин'), ('In Delivery to Client', 'В доставке клиенту'), ('Delivered', 'Доставлен')])
    delivery = SelectField('Доставщик', coerce=int)
    submit = SubmitField('Обновить статус')

# Маршруты
@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        if current_user.role == 'Client':
            return redirect(url_for('order'))
        elif current_user.role == 'Manager':
            return redirect(url_for('manager_orders'))
        elif current_user.role == 'Delivery':
            return redirect(url_for('delivery_orders'))
    return render_template('home.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role=form.role.data)
        db.session.add(user)
        db.session.commit()
        flash('Ваш аккаунт создан! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Вход не выполнен. Пожалуйста, проверьте электронную почту и пароль.', 'danger')
    return render_template('login.html', title='Вход', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        current_user.password = hashed_password
        db.session.commit()
        flash('Ваш аккаунт был обновлён!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('profile.html', title='Аккаунт', form=form)

@app.route("/order", methods=['GET', 'POST'])
@login_required
def order():
    if current_user.role != 'Client':
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('home'))
    form = OrderForm()
    if form.validate_on_submit():
        order = Order(
            client_id=current_user.id,
            product_name=form.product_name.data,
            client_name=form.client_name.data,
            client_phone=form.client_phone.data,
            delivery_address=form.delivery_address.data,
            delivery_time=form.delivery_time.data,
            payment_method=form.payment_method.data
        )
        db.session.add(order)
        db.session.commit()
        flash('Ваш заказ был оформлен!', 'success')
        return redirect(url_for('home'))
    return render_template('client_order.html', title='Оформить заказ', form=form)

@app.route("/manager_orders")
@login_required
def manager_orders():
    if current_user.role != 'Manager':
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('home'))
    orders = Order.query.all()
    return render_template('manager_orders.html', title='Управление заказами', orders=orders)

@app.route("/order/<int:order_id>/update", methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    if current_user.role != 'Manager':
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('home'))
    form = OrderStatusForm()
    form.delivery.choices = [(u.id, u.username) for u in User.query.filter_by(role='Delivery').all()]
    if form.validate_on_submit():
        order.status = form.status.data
        order.delivery_id = form.delivery.data
        db.session.commit()
        flash('Статус заказа обновлён!', 'success')
        return redirect(url_for('manager_orders'))
    elif request.method == 'GET':
        form.status.data = order.status
        form.delivery.data = order.delivery_id
    return render_template('update_order.html', title='Обновить заказ', form=form, order=order)

@app.route("/delivery_orders")
@login_required
def delivery_orders():
    if current_user.role != 'Delivery':
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('home'))
    orders = Order.query.filter_by(delivery_id=current_user.id).all()
    return render_template('delivery.html', title='Заказы на доставку', orders=orders)

# Функция для создания базы данных
def create_database():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        create_database()
    app.run(debug=True)
