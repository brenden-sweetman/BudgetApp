# Main Flask imports
from app import app
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for

# Database imports
from .database import Base, engine, SessionLocal
from .database import Transactions, NetBudget
import datetime

# Needed for task scheduler
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler


@app.route('/')
def home():
    return redirect(url_for('input'))

@app.route('/input')
def input():
    return render_template("input.html", title="Input", categories = budgetDict.keys() )

@app.route("/processInput", methods=['POST'])
def processInput():
    data = request.form
    amount = float(data.get('amount',0))
    if data.get('deposit',"off") != "on":
        amount = amount * -1
    SessionLocal.add(Transactions(name=data.get('name',""), category=data.get('category',""), cost=amount, notes=data.get('notes',"")))
    SessionLocal.commit()
    SessionLocal.remove()
    netBudgetCalculation()
    return redirect(url_for('seeNetData'))

@app.route("/seeData")
def seeData():
    # Get TimeDelta for current month:
    currentTime = datetime.datetime.today()
    firstDay = datetime.datetime(currentTime.year,currentTime.month,1)
    timeDiff =  currentTime-firstDay

    transactions = SessionLocal.query(Transactions).filter(Transactions.created > timeDiff).all()
    SessionLocal.remove()
    try:
        renderPage = render_template("summary.html",transactions=transactions, title = "Monthy Transactions")
    except Exception as e:
        renderPage = render_template("error.html", error=str(e))
    return renderPage

@app.route("/seeNetData")
def seeNetData():
    ## Create dictonary of all transactions
    # Get TimeDelta for current month:
    timeDiff =  getMonthStart()
    # Pull all trsactions
    transDict = dict.fromkeys(budgetDict.keys(), [])
    monthTrasactions = SessionLocal.query(Transactions).filter(Transactions.created > timeDiff).all()
    # Build dictonary of all transactions
    for key in transDict:
        tempList = []
        for trans in monthTrasactions:
            if trans.category == key:
                tempList.append(trans)
        transDict[key] = tempList    
    # Get all categories
    netCategories = SessionLocal.query(NetBudget).all()
    SessionLocal.remove()
    # Calculate total monthy spending
    total = 0.0
    for value in [i.net_value for i in netCategories]:
        total = total + value
    try:
        renderPage = render_template("netSummary.html",netCategories=netCategories, title = "Monthy Totals", total=total, transDict=transDict)
    except Exception as e:
        renderPage = render_template("error.html", error=str(e))
    return renderPage


def netBudgetCalculation():
    # Get TimeDelta for current month:
    timeDiff =  getMonthStart()

    categories = dict.fromkeys(budgetDict.keys(), 0.0)
    # Query all trasactions for this month
    monthTransactions = SessionLocal.query(Transactions).filter(Transactions.created > timeDiff).all()
    # Calculate budget left for each category
    for transaction in monthTransactions:
        try:
            if transaction.category != '':
                categories[transaction.category] = categories[transaction.category] + transaction.cost
        except KeyError:
            print (KeyError)


    # Update NetBudget table
    dbValues = SessionLocal.query(NetBudget).all()
    dbCat = [i.category for i in dbValues]
    for key, value in categories.items():
        # add value to monthly total
        if key in dbCat:
            # debug: print (key + " is in DB")
            # Update row with net value
            updateRow = SessionLocal.query(NetBudget).filter(NetBudget.category == key).one()
            updateRow.net_value = value
            SessionLocal.commit()
        else:
            # debug print (key + " is not in DB")
            # Create row for new category
            newRow = NetBudget(category = key, net_value = value)
            SessionLocal.add(newRow)
            SessionLocal.commit()
    # Close db session
    SessionLocal.remove()

## Function to find time delta to start of month
def getMonthStart():
    # Get TimeDelta for current month:
    currentTime = datetime.datetime.today()
    firstDay = datetime.datetime(currentTime.year,currentTime.month,1)
    return currentTime-firstDay

### Jinja2 custom functions

# This handles dates in a template
@app.template_filter('dateRender')
def dateRender(date,dateStr):
    try:
        return date.strftime(dateStr)
    except:
        return "None"
@app.template_filter('moneyRender')
def moneyRender(amount,positive = False):
    if positive and amount != 0:
        amount = amount * -1
    return "$"+str(round(amount,2))
@app.template_filter('removeSpace')
def removeSpace(s):
    return s.replace(" ","")

### This will run on start of app:
# Pull in current budget values and categories
budgetFile = open("app/static/budget.txt",'r')
budgetDict = {}
for line in budgetFile.readlines():
     line = line.split(":")
     budgetDict[line[0]] = float(line[1])
budgetFile.close()

## (Disable for now) Should run after every new trasaction
# Start net calculation task to run every min
#scheduler = BackgroundScheduler()
#scheduler.add_job(func=netBudgetCalculation, trigger="interval", seconds=60)
#scheduler.start()
# Shut down the scheduler when exiting the app
#atexit.register(lambda: scheduler.shutdown())
