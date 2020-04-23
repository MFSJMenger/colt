from flask import render_template
from flask import request
#
from . import app
from .forms import QuestionForm
import json
#

question = """
key = :: str :: [hi, du, mhm]

[a]
hi = 25 :: int
b = case

[a::b(case)]
c = :: int
d = :: int
e = :: float :: [1.0, 2.0, 3.0]
f = :: list

[a::b(case)::qchem]
c = :: int
d = :: int
e = :: float :: [1.0, 2.0, 3.0]
f = :: list
[a::b(case)::qchem::case(select)]
c = :: int
d = :: int
e = :: float :: [1.0, 2.0, 3.0]
f = :: list

[a::b(case)::qchem::case(select2)]
c = :: int
d = :: int
e = :: float :: [1.0, 2.0, 3.0]
f = :: list


[a::b(casetwo)]
c = 8 :: int

"""


qform = QuestionForm(question)


@app.route('/', methods=['GET', 'POST'])
def questions():
    return render_template('question.html', **{
        'qname': "questions",
        'container': 'container',
        'setup': "/setup",
        'validation': "/validate",
        'selectupdate': "/update_select",
        })

@app.route("/setup", methods=['GET', 'POST'])
def question_setup():
    try:
        json_sent = request.get_json()
    except Exception as e:
        print("exception ", str(e))
        return 
    setup = qform.generate_setup()
    response = app.response_class(
        response=json.dumps(setup),
        status=200,
        mimetype='application/json')
    return response


@app.route("/update_select", methods=['GET', 'POST'])
def question_update_select():
    try:
        json_sent = request.get_json()
    except Exception as e:
        print("exception ", str(e))
        return 
    name = json_sent['name']
    value = json_sent['value']
    if value == "":
        return app.response_class(
        response=json.dumps({}),
        status=200,
        mimetype='application/json')
    #
    block, key = qform.split_keys(name)
    #
    block = qform.blocks[block]
    if key in block.blocks:
        select = block.blocks[key]
        if value == select.answer:
            out = {}
        else:
            delete = select.get_delete_blocks()
            # update answer
            select.answer = value
            setup = select.generate_setup()
            out = {'delete': delete,
                   'setup': setup}
    else:
        out = {}
    response = app.response_class(
        response=json.dumps(out),
        status=200,
        mimetype='application/json')
    return response


@app.route("/validate", methods=['GET', 'POST'])
def question_validation():
    try:
        json_sent = request.get_json()
    except Exception as e:
        print("exception ", str(e))
        return 
    name = json_sent['name']
    value = json_sent['value']
    #
    block, key = qform.split_keys(json_sent['name'])
    #
    block = qform.blocks[block]
    try:
        block.concrete[key].answer = value
        answer = """{"answer": true}"""
    except ValueError:
        answer = """{"answer": false}"""

    response = app.response_class(
        response=answer,
        status=200,
        mimetype='application/json')
    return response
