from Website import create_app #import create_app func from Websute module

app = create_app() #apply the func to initialize the Flask application

if __name__ == "__main__": #the "__main__" makes sure this code runs only when u start the script urself
    app.run(debug=True) #run flask application