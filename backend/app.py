from flask import Flask, abort, flash, jsonify, redirect, request, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from sqlalchemy.exc import NoResultFound
from shared.auth import Auth, usher, planner
from typing import Union
import datetime
import random



app = Flask(__name__)
app.config['SECRET_KEY'] = 'df02efcafd88339a979746fe'


bcrypt = Bcrypt(app)



AUTH = Auth()
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id: str) -> Union[None, usher.Usher, planner.Planner]:
    try:
       user = AUTH.db.searchitem(usher.Usher, id=user_id)
       return user
    except NoResultFound:
       try:
          user = AUTH.db.searchitem(planner.Planner, id=user_id)
          return user
       except NoResultFound:
         return None


@app.route("/", strict_slashes=False)
def index() -> str:
    """GET /
     Return:
    - The home page's payload.
    """
    return render_template('home.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    ### Change request.args.get() to request.form.get() ####
    password = request.form.get('password')
    username = request.form.get('username')
    usertype = request.form.get('usertype')
    email = request.form.get('email')
    
    if not password:
      return jsonify({"ERR": "Password is required"})

    hashed_password = bcrypt.generate_password_hash(password)
   
    ### the usertype determines what type of user is registering (usher or planner)
    user = AUTH.register_user(usertype, username=username, password=hashed_password, email=email)
    if user is None:
      return jsonify({"ERR": "User already exist"})
    else:
      return jsonify({user.username: user.get_data()})


@app.route('/login', methods=['POST', 'GET'])
def login():
   try:
      ### Change request.args.get() to request.form.get() ####
      username, password = (request.form.get('username'), request.form.get('password'))
      usertype = request.form.get('usertype')
      session_id = request.cookies.get("session")

      #Usertype determines what kind of user is logging-in (usher or planner)
      user = AUTH.login_user(usertype, username=username, password=password)
      if user is not None:
         login_user(user)
         AUTH.set_session(user, session_id)
         """login_user(user)
          redirect_url = request.args.get("next")
          if redirect_url is not None:
             return redirect(redirect_url)"""
         return jsonify(user.get_data())
      else:
         return jsonify({"ERROR" : "USER NOT FOUND IN DB"})
   except NoResultFound as err:
       return jsonify({"Error": err.args[0], "reason" : "unauthorized user or invalid login reqst"})


"""@app.route('/dashboard', strict_slashes=False, methods=['GET', 'POST'])
@login_required
def dashboard():
   user : Union[usher.Usher | planner.Planner] = current_user
   return jsonify({"user": user.username}) """


@app.route("/users/<user_type>", methods=["GET"])
def users(user_type):
   models = {"usher" : usher.Usher, "planner": planner.Planner}
   if user_type is None:
      return abort(400)
   try:
      users = AUTH.db.list_all_users(models.get(user_type))
      return jsonify({"users" : users})
   except:
      return abort(400)


@app.route("/user/<user_type>/<user_id>", methods=["GET"])
def user(user_type, user_id):
   models = {"usher" : usher.Usher, "planner": planner.Planner}
   if user_type is None:
      return abort(400)
   if user_id is None:
      try:
         users = AUTH.db.list_all_users(models.get(user_type))
         return jsonify({"users" : users})
      except:
         return abort(400)
   try:
      user = AUTH.db.searchitem(models.get(user_type), id=user_id)
      return jsonify({"user" : user.username})
   except NoResultFound:
      return jsonify({"err" : "No result found"})

@app.route('/forgot-password', methods=["POST", "GET"])
def forgot_password():
   email = request.form.get('email')
   try:
      try:
         print("SEARCHING PLANNER...........................")
         user = AUTH.db.searchitem(planner.Planner, email=email)
         token = random.randbytes(6).hex()
         updated_user = AUTH.update_item("planner", user.id, {'_rand_auth':token})
         return jsonify({"token": updated_user._rand_auth})
      except:
         try:
            print("SEARCHING USHER........................")
            user = AUTH.db.searchitem(usher.Usher, email=email)
            token = random.randbytes(6).hex()
            updated_user = AUTH.update_item("usher", user.id, {'_rand_auth':token})
            return jsonify({"token": updated_user._rand_auth})
         except:
            return jsonify({"error": "User not found"})
   except:
      return abort(400)


@app.route('/reset-password/<token>', methods=['POST', 'GET'])
def reset_password(token):
   email = request.form.get('email')
   new_password = request.form.get("new_password")
   try:
      try:
         user = AUTH.db.searchitem(planner.Planner, email=email)
         if token == user._rand_auth:
            hashed_password = bcrypt.generate_password_hash(new_password)
            AUTH.update_item("planner", user.id, {'password':hashed_password})
            return jsonify({"status" : "ok"})
         else:
            return jsonify({"err": "Invalid Token"})
      except:
         user = AUTH.db.searchitem(usher.Usher, email=email)
         if token == user._rand_auth:
            hashed_password = bcrypt.generate_password_hash(new_password)
            AUTH.update_item("usher", user.id, {'password':hashed_password})
            return jsonify({"status" : "ok"})
         else:
            return jsonify({"err": "Invalid Token"})
   except:
      return abort(400)

   
@app.route("/postjob", methods=["GET", "POST"])
@login_required
def postjob():
   description = request.form.get("description")
   payment_amount = request.form.get("payment_amount")
   if description is None or payment_amount is None:
      abort(400)
   # ensure all forms fields are collected using request.form.get() and passed as
   # second arguments to the AUTH.search_secific_table() function below
   user = current_user
   confirmed_user = AUTH.search_specific_table("planner", id=user.id)
   if confirmed_user is None:
      abort(400)
   try:
      job = AUTH.db.postjob(confirmed_user.id, {"job_description":description, "job_amount":payment_amount})
      return jsonify({"status" : job.db_id})
   except:
      abort(400)
   
@app.route("/hire/<usher_id>/<job_id>")
@login_required
def hire(usher_id, job_id):
   try:
      job = AUTH.hire(usher_id, job_id)
      return jsonify({"status": job})
   except:
      abort(400)

@app.route("/update/<user_type>/<user_id>/<update_param>", methods=["POST"])
@login_required
def update_user(user_type, user_id, update_param):
   param = request.form.get(update_param)
   try:
      updated_user = AUTH.update_item(user_type, user_id, {update_param:param})
      return jsonify({"status" : "ok", "response" : updated_user.age})
   except:
      abort(400)
   
   
@app.route('/logout', methods=['GET','POST'])
def logout():
  logout_user()
  return redirect('/')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="3000", debug=True)
