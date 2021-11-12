from flask import Flask, request, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from functools import wraps
from flask import abort
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("CONFIG_SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

secret_master = os.environ.get("SSECRET")


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    print(f"LOGGED USER ID:{user_id}")
    return User.query.get(int(user_id))

##CONFIGURE TABLES


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    #*******Add parent relationships*******#
    #This will act like a List of BlogPost objects attached to each User.
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    #This will act like a List of Comment objects attached to each User.
    #The "comment_author" refers to the author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # author = db.Column(db.String(250), nullable=False)

    #*******Add child relationship to User*******#
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    #*******Add parent relationship to Comment*******#
    comments = relationship("Comment", back_populates="commented_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    #*******Add child relationship to User*******#
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    #Create reference to the Comment object, the "comments" refers to the comments protperty in the User class.
    comment_author = relationship("User", back_populates="comments")

    #*******Add child relationship to BlogPost*******#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    commented_post = relationship("BlogPost", back_populates="comments")

    text = db.Column(db.Text, nullable=False)

## Only first time to create DBs
# db.create_all()


# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 (admin id) then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        print("ALL GOOD MASTER")
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    if current_user.is_authenticated and current_user.id == 1:
        user_is_admin = True
        print("User is ADMIN")
    elif current_user.is_authenticated:
        print(f"CUR USER FOR POST: {current_user}")
        user_is_admin = False
    else:
        user_is_admin = False
        print("No user authenticated")
    ## Or with exception
    # try:
    #     if current_user.id == 1:
    #         user_is_admin = True
    # except AttributeError:
    #     user_is_admin = False
    return render_template("index.html", all_posts=posts, current_user=current_user, user_is_admin=user_is_admin)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=request.form.get('email')).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            password=hash_and_salted_password,
            name=form.name.data,
        )
        db.session.add(new_user)
        db.session.commit()

        # Log in and authenticate user after adding details to database.
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        print(f"Email: {email}")
        password = login_form.password.data
        print(f"Pasword: {password}")

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            # print("That email does not exist, please try again.")
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            # print("Password incorrect, please try again.")
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Email exists and password correct
        else:
            print(f"USER IN with ID: {user.id}!")
            # Log in and authenticate user after adding details to database.
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=login_form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    print("USER LOGGED OUT")
    # current_user.is_authenticated = False
    # return redirect(url_for('get_all_posts', current_user=current_user))
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_post = Comment.query.all()
    # users = User.query.all()
    comments = []
    for comment in comment_post:
        if comment.post_id == post_id:
            commenter = User.query.filter_by(id=comment.author_id).first()
            comments.append({
                "name": commenter.name,
                "email": commenter.email,
                "text": comment.text})
            print(commenter.name)
    print(comments)

    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        print(f"{current_user.name} comment: {comment_form.body.data}")
        new_comment = Comment(
            text=comment_form.body.data,
            author_id=current_user.id,
            post_id=post_id
             )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    requested_post = BlogPost.query.get(post_id)
    if current_user.is_authenticated and current_user.id == 1:
        user_is_admin = True
        print("User is ADMIN")
    elif current_user.is_authenticated:
        user_is_admin = False
        print(f"CURRENT USER: {current_user}")
    else:
        user_is_admin = False
        print("No user")
    ## Or with exception
    # try:
    #     if current_user.id == 1:
    #         user_is_admin = True
    # except AttributeError:
    #     user_is_admin = False

    return render_template("post.html", post=requested_post, current_user=current_user, user_is_admin=user_is_admin,
                           form=comment_form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
## Mark with decorator ?
# @login_required
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
# Mark with decorator
@admin_only
def add_new_post():
    print(f"CUR USER NAME: {current_user.name}")
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
# Mark with decorator
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=current_user.name,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
# Mark with decorator
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts', current_user=current_user))


if __name__ == "__main__":
    app.run(debug=True)
