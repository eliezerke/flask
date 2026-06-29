from flask import Flask, render_template

app = Flask(__name__)
app.config["SECReT-KEY"] = "nowdwhdfuiwefydf7e23qfid3dwe9dfwqidhwfuebflqwiof2w837773ydwd"

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()