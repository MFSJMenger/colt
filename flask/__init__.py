from flask import Flask

app = Flask(__name__)

from jsapp import routes
