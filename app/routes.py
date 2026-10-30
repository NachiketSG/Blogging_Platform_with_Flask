from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from app.models import User, Post, Tag, Comment
from app.forms import LoginForm, RegistrationForm, PostForm, CommentForm

bp = Blueprint('main', __name__)

# --- WEEK 2: AUTHENTICATION ---
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# --- WEEK 4 & 6: HOME, PAGINATION, SEARCH ---
@bp.route('/')
@bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '') # Week 6: Search
    
    if query:
        posts = Post.query.filter(Post.title.contains(query) | Post.content.contains(query)).order_by(Post.timestamp.desc()).paginate(page=page, per_page=5, error_out=False)
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=5, error_out=False)
        
    return render_template('index.html', title='Home', posts=posts, query=query)

# --- WEEK 3: POST CRUD ---
@bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        
        # Handle Tags
        if form.tags.data:
            tag_names = [t.strip().lower() for t in form.tags.data.split(',')]
            for name in tag_names:
                if name:
                    tag = Tag.query.filter_by(name=name).first()
                    if not tag:
                        tag = Tag(name=name)
                    post.tags.append(tag)
                    
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('main.index'))
    return render_template('post.html', title='New Post', form=form, is_view=False) # Explicitly set is_view=False

@bp.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm() # Week 5: Comments
    
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('You need to login to comment.')
            return redirect(url_for('main.login'))
        comment = Comment(body=form.body.data, post=post, author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('main.post', id=post.id))
        
    return render_template('post.html', title=post.title, post=post, form=form, is_view=True)

# --- NEW: EDIT POST ---
@bp.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    # Security check: Only author can edit
    if post.author != current_user:
        flash('You cannot edit this post.')
        return redirect(url_for('main.index'))
    
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        
        # Update tags
        post.tags = [] # Clear old tags first
        if form.tags.data:
            tag_names = [t.strip().lower() for t in form.tags.data.split(',')]
            for name in tag_names:
                if name:
                    tag = Tag.query.filter_by(name=name).first()
                    if not tag:
                        tag = Tag(name=name)
                    post.tags.append(tag)
                    
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.post', id=post.id))
    elif request.method == 'GET':
        # Pre-fill form with existing data
        form.title.data = post.title
        form.content.data = post.content
        form.tags.data = ", ".join([tag.name for tag in post.tags])
        
    return render_template('post.html', title='Edit Post', form=form, is_view=False)

# --- NEW: DELETE POST ---
@bp.route('/post/<int:id>/delete', methods=['POST'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    if post.author != current_user:
        flash('You cannot delete this post.')
        return redirect(url_for('main.index'))
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.')
    return redirect(url_for('main.index'))

# --- NEW: USER PROFILE ---
@bp.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    # Get all posts by this user
    posts = Post.query.filter_by(author=user).order_by(Post.timestamp.desc()).all()
    return render_template('user_profile.html', title='Profile', user=user, posts=posts)

# --- WEEK 6: FILTER BY TAG ---
@bp.route('/tag/<name>')
def tag_filter(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = tag.posts.order_by(Post.timestamp.desc()).paginate(page=page, per_page=5, error_out=False)
    return render_template('index.html', title=f'Tag: {name}', posts=posts, query='')