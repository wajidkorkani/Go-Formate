from flask import Flask, request, render_template as render, redirect, url_for

app = Flask(__name__)

@app.route('/')
def Home():
  return render("index.html", text="Flask")

@app.route('/form')
def Form():
  return render('form.html')



app.run(debug=True)