import subprocess, os, json, time, ctypes
from flask import Flask, render_template, request, redirect, url_for, flash, Response, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from passlib.hash import pbkdf2_sha256
from influxdb_client import InfluxDBClient
from datetime import datetime
import pandas as pd

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")


# -- single-user credentials stored in user.json --
CRED_FILE = "user.json"
if not os.path.exists(CRED_FILE):
    with open(CRED_FILE, "w") as f:
        json.dump({
            "username": "admin",
            "password_hash": pbkdf2_sha256.hash("admin")
        }, f)

time.sleep(1)

with open(CRED_FILE) as f:
    creds = json.load(f)

login_mgr = LoginManager(app)
login_mgr.login_view = "login"
login_mgr.login_message = "Please log in to access this page."

class User(UserMixin):
    def get_id(self):
        # always return the current username from creds
        return creds["username"]

@login_mgr.user_loader
def load_user(user_id):
    # only accept the one user, whose username lives in creds["username"]
    if user_id == creds["username"]:
        return User()
    return None


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u, pw = request.form["username"], request.form["password"]
        if u==creds["username"] and pbkdf2_sha256.verify(pw, creds["password_hash"]):
            login_user(User())
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        new_user = request.form.get("new_username", "").strip()
        new_pw   = request.form.get("new_password", "").strip()

        if not new_user or not new_pw:
            flash("Both username and password are required.", "error")
            return render_template("change_password.html")

        # Write updates back to disk
        creds["username"]      = new_user
        creds["password_hash"] = pbkdf2_sha256.hash(new_pw)
        with open(CRED_FILE, "w") as f:
            json.dump(creds, f)

        # Invalidate the current session so they must log in again
        logout_user()
        flash("Credentials updated! Please sign in with your new username and password.")
        return redirect(url_for("login"))

    return render_template("change_password.html")

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

BUCKET=os.environ.get("INFLUX_BUCKET","mybucket")

@app.route("/data")
@login_required
def data():
    # read range from URL, default to “1h”
    rng = request.args.get("range", "1h")
    client = InfluxDBClient(
        url=os.environ["INFLUX_URL"],
        token=os.environ["INFLUX_TOKEN"],
        org=os.environ["INFLUX_ORG"]
    )

    # if the client requests “all”, don’t use a negative duration (which fails)
    if rng == "all":
        # pull every point by starting at the Unix epoch
        flux = f'''
          from(bucket:"{BUCKET}")
            |> range(start: 0)
            |> pivot(
                 rowKey:["_time"],
                 columnKey: ["_field"],
                 valueColumn: "_value"
               )
        '''
    else:
        flux = f'''
          from(bucket:"{BUCKET}")
            |> range(start: -{rng})
            |> pivot(
                 rowKey:["_time"],
                 columnKey: ["_field"],
                 valueColumn: "_value"
               )
        '''
    df = client.query_api().query_data_frame(flux)

    # if InfluxDB returned zero rows, just send back []
    if df.empty:
        return Response("[]", mimetype="application/json")

    if "Payload_Message" in df.columns:
        parsed = df["Payload_Message"].apply(json.loads).apply(pd.Series)
        df = pd.concat([df.drop(columns=["Payload_Message"]), parsed], axis=1)

    df["_time"] = df["_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df[["_time", "PM1", "PM2", "PM10", "T", "H"]]

    return Response(df.to_json(orient="records"), mimetype="application/json")

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings_file = 'settings.json'
    if request.method == 'POST':
        # write the submitted setting to file
        new_value = request.form.get('setting_value', '')
        with open(settings_file, 'w') as f:
            f.write(new_value)
        return redirect(url_for('settings'))

    # on GET, load the current setting (or default to empty)
    try:
        with open(settings_file) as f:
            setting_value = f.read()
    except (FileNotFoundError):
        setting_value = ''

    return render_template('settings.html', setting_value=setting_value)

@app.route('/delete-data', methods=['POST'])
@login_required
def delete_data():
    """
    Deletes every point in the InfluxDB bucket.
    """
    client = InfluxDBClient(
        url=os.environ["INFLUX_URL"],
        token=os.environ["INFLUX_TOKEN"],
        org=os.environ["INFLUX_ORG"]
    )
    delete_api = client.delete_api()

    # delete everything from the Unix epoch until now
    start = "1970-01-01T00:00:00Z"
    stop  = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # predicate = '' means “no filter, delete all”
    delete_api.delete(start, stop, predicate='', bucket=BUCKET, org=os.environ["INFLUX_ORG"])

    return ('', 204)  # 204 No Content

if __name__ == "__main__":
    # fallback for local dev if you skip Gunicorn
    app.run(host="0.0.0.0", port=443,
            ssl_context=("/certs/cert.pem", "/certs/key.pem"))
