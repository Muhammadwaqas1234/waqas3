import os
import uuid
from datetime import datetime, timedelta
import openai
import boto3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from gtts import gTTS
from boto3.dynamodb.conditions import Key, Attr
from llama_index.core import VectorStoreIndex, ServiceContext
from llama_index.core.prompts.base import ChatPromptTemplate
from llama_index.llms.openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import base64
import stripe
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
dynamodb_client = boto3.client('dynamodb', region_name='ap-southeast-2')

openai.api_key = os.getenv("OPENAI_API_KEY")
messages = []
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'helpscai@gmail.com'
app.config['MAIL_PASSWORD'] = 'qihtnzfigqpjbjfm'
app.config['MAIL_DEFAULT_SENDER'] = 'helpscai@gmail.com'
openai_api_key = os.getenv('OPENAI_API_KEY')
stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')
stripe_price_id = os.getenv('STRIPE_PRICE_ID')
stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
mail = Mail(app)


users_table = dynamodb.Table('Users')
chat_history_table = dynamodb.Table('ChatHistory')
feedback_table = dynamodb.Table('Feedback')
data_table = dynamodb.Table('Data')

def appendMessage(role, message, type='message'):
    messages.append({"role": role, "content": message, "type": type})

def fetch_data_from_dynamodb(category, subcategory):
    response = data_table.query(
        IndexName='category-index', 
        KeyConditionExpression=Key('category').eq(category)
    )
    items = response['Items']
    if not items:
        return []

    filtered_items = [item for item in items if item['subcategory'] == subcategory]
    return filtered_items

def load_data(category, subcategory):
    data_items = fetch_data_from_dynamodb(category, subcategory)
    documents = [item['content'] for item in data_items]
    
    llm = OpenAI(model="gpt-3.5-turbo", temperature="0.1", systemprompt="""Use the data from DynamoDB as source for the answer. Generate a valid 
                 and relevant answer to a query related to 
                 construction problems, ensure the answer is based strictly on the content of 
                 the data and not influenced by other sources. Do not hallucinate. The answer should 
                 be informative and fact-based. """)
    service_content = ServiceContext.from_defaults(llm=llm)
    index = VectorStoreIndex.from_documents(documents, service_context=service_content)
    return index

def query_chatbot(query_engine, user_question):
    response = query_engine.query(user_question)
    return response.response if response else None

def initialize_chatbot(category, subcategory, model="gpt-3.5-turbo", temperature=0.4):
    data_items = fetch_data_from_dynamodb(category, subcategory)
    documents = [item['content'] for item in data_items]
    llm = OpenAI(model=model, temperature=temperature)

    additional_questions_prompt_str = (
        "Given the context below, generate only one additional question different from previous additional questions related to the user's query:\n"
        "Context:\n"
        "User Query: {query_str}\n"
        "Chatbot Response: \n"
    )

    new_context_prompt_str = (
        "We have the opportunity to only one generate additional question different from previous additional questions based on new context.\n"
        "New Context:\n"
        "User Query: {query_str}\n"
        "Chatbot Response: \n"
        "Given the new context, generate only one additional questions different at each time from previous additional questions related to the user's query."
        "If the context isn't useful, generate only one additional questions different at each from previous time from previous additional questions based on the original context.\n"
    )

    chat_text_qa_msgs = [
        (
            "system",
            """Generate only one additional question that facilitates deeper exploration of the main topic 
            discussed in the user's query and the chatbot's response. The question should be relevant and
              insightful, encouraging further discussion and exploration of the topic. Keep the question concise 
              and focused on different aspects of the main topic to provide a comprehensive understanding.""",
        ),
        ("user", additional_questions_prompt_str),
    ]
    text_qa_template = ChatPromptTemplate.from_messages(chat_text_qa_msgs)

    chat_refine_msgs = [
        (
            "system",
            """Based on the user's question '{prompt}' and the chatbot's response '{response}', please 
            generate only one additional question related to the main topic. The question should be 
            insightful and encourage further exploration of the main topic, providing a more comprehensive 
            understanding of the subject matter.""",
        ),
        ("user", new_context_prompt_str),
    ]
    refine_template = ChatPromptTemplate.from_messages(chat_refine_msgs)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
    )

    return query_engine

def generate_response(user_question):
    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')
    user_language = user.get('language', 'en') if user else 'en'

    # Identify relevant category and subcategory
    # This part needs to be customized based on how you identify the category and subcategory from the question
    category = "your_category"  # Replace with logic to identify category from question
    subcategory = "your_subcategory"  # Replace with logic to identify subcategory from question

    index = load_data(category, subcategory)
    chat_engine = index.as_chat_engine(chat_mode="condense_question", verbose=True)

    response = chat_engine.chat(user_question)
    if response:
        response_text = response.response

        tts = gTTS(text=response_text, lang=user_language)
        tts.save('output.wav')

        with open('output.wav', 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')

        additional_questions = generate_additional_questions(user_question)
        document_session = response_text

        return response_text, additional_questions, audio_data, document_session

    return None, None, None, None

def generate_additional_questions(user_question):
    additional_questions = []
    words = ["1", "2", "3"]
    for word in words:
        question = query_chatbot(initialize_chatbot(), user_question)
        additional_questions.append(question if question else None)

    return additional_questions

@app.route("/chat", methods=["POST"])
def chat():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"})

    user_question = request.json["user_question"]
    user_id = session['user_id']

    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')
    if user:
        last_question_date = datetime.fromisoformat(user.get('last_question_date', '1970-01-01')).date()
        current_date = datetime.utcnow().date()

        if last_question_date < current_date:
            user['question_count'] = 0

        question_limit = 10 if user.get('user_type') == 'pro' else 5

        if user['question_count'] >= question_limit:
            return jsonify({"error": f"{user['user_type'].capitalize()} user has reached maximum question limit"})

        user['question_count'] += 1
        user['last_question_date'] = current_date.isoformat()
        users_table.put_item(Item=user)

        response_text, additional_questions, audio_data, document_session = generate_response(user_question)
        appendMessage('user', user_question)
        appendMessage('assistant', response_text, type='response')

        session_id = str(uuid.uuid4())
        session_name = ' '.join(user_question.split()[:4])  
        timestamp = datetime.utcnow().isoformat()  
        chat_history_table.put_item(
            Item={
                "session_id": session_id,
                "user_id": user_id,
                "session_name": session_name,
                "start_time": timestamp,
                "chat_history": messages,
                "timestamp": timestamp  
            }
        )

        return jsonify({"response_text": response_text, "additional_questions": additional_questions, "audio_data": audio_data, "document_session": document_session})

    return jsonify({"error": "User not found"})

def time_since(timestamp):
    now = datetime.utcnow()
    time_diff = now - timestamp

    if time_diff < timedelta(minutes=1):
        return "just now"
    elif time_diff < timedelta(hours=1):
        return f"{int(time_diff.total_seconds() // 60)} minutes ago"
    elif time_diff < timedelta(days=1):
        return f"{int(time_diff.total_seconds() // 3600)} hours ago"
    elif time_diff < timedelta(weeks=1):
        return f"{int(time_diff.total_seconds() // 86400)} days ago"
    else:
        return f"{int(time_diff.total_seconds() // 604800)} weeks ago"

@app.route("/history")
def history():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = chat_history_table.query(
        KeyConditionExpression=Key('user_id').eq(user_id),
        ScanIndexForward=False  
    )
    items = response['Items']
    chat_history = []
    for item in items:
        timestamp = datetime.fromisoformat(item['start_time'])
        chat_history.append({
            "session_name": item['session_name'],
            "time_since": time_since(timestamp),
            "chat_history": item['chat_history']
        })

    return render_template("history.html", chat_history=chat_history)

@app.route('/send-email', methods=['POST'])
def send_email():
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']
    attachments = request.files.getlist('attachments')

    msg = Message(subject, recipients=['helpscai@gmail.com'])
    msg.body = f"From: {email}\n\n{message}"

    for attachment in attachments:
        msg.attach(attachment.filename, attachment.content_type, attachment.read())

    try:
        mail.send(msg)
        return jsonify({'message': 'Email sent successfully!'}), 200
    except Exception as e:
        return jsonify({'message': 'Error sending email.'}), 500
        
@app.route("/save_language", methods=["POST"])
def save_language():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']
    language = request.json.get("language")

    if not language:
        return jsonify({"error": "No language provided"}), 400

    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        user['language'] = language
        users_table.put_item(Item=user)
        return jsonify({"success": "Language preference saved"}), 200

    return jsonify({"error": "User not found"}), 404






@app.route("/")
def home():
    if 'username' in session:
        user = session.get("user")
        return render_template("index.html" , messages=messages , user=user)
    return render_template("home.html")

@app.route("/index")
def index():
    if 'username' in session:
        user = session.get("user")
        return render_template("index.html", user=user)
    return redirect(url_for("login"))



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first"]
        last_name = request.form["last"]
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        user_type = "basic"

        
        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )
        if response['Items']:
            return render_template("register.html", error="Email already registered.")

        user_id = str(uuid.uuid4())
        registration_date = datetime.utcnow().isoformat()

        users_table.put_item(
            Item={
                "id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "password": password,
                "email": email,
                "registration_date": registration_date,
                "user_type": user_type,  
                "question_count": 0,
                "last_question_date": registration_date
            }
        )
        
        session["username"] = username
        session["user_id"] = user_id
        session["user"] = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

        return redirect(url_for("subscribe"))
    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )

        if response['Items']:
            session["username"] = response['Items'][0]['username']
            session["user_id"] = response['Items'][0]['id']  
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")






@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        if request.method == "POST":
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if user['password'] != current_password:
                return render_template("index.html", error="Current password is incorrect")

            if new_password != confirm_password:
                return render_template("index.html", error="Passwords do not match")

            user['password'] = new_password
            users_table.put_item(Item=user)

            return redirect(url_for('account'))

        return render_template("index.html")

    return redirect(url_for('index'))

@app.route("/account")
def account():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        user_data = {
            "username": user['username'],
            "email": user['email'],
            "password": user['password']
        }
        return render_template("account.html", user=user_data)
    return redirect(url_for('index'))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

from datetime import datetime, timedelta




@app.route("/support", methods=["GET", "POST"])
def support():
    if request.method == "POST":
        if 'username' not in session:
            return jsonify({"error": "User not logged in"})

        user_id = session['user_id']
        message = request.form["message"]

        feedback_table.put_item(Item={
            'user_id': user_id,
            'timestamp': str(datetime.utcnow()),
            'feedback': message
        })

        return render_template("feedback_submitted.html")

    return render_template("support.html")

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    #session.pop('user', None)
    return redirect(url_for('login'))


def handle_checkout_session(session):
    print("Handling checkout session...")
    customer_email = session['customer_details']['email']
    print(f"Customer email: {customer_email}")

    response = users_table.scan(FilterExpression=Attr('email').eq(customer_email))
    users = response['Items']

    if users:
        user = users[0]
        print(f"Found user: {user}")

        user['user_type'] = 'pro'
        users_table.put_item(Item=user)
        print(f"Updated user: {user}")
    else:
        print("User not found")

    print("Checkout session handling complete.")


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    print("Webhook received")
    payload = request.get_data(as_text=True)
    print("Payload:", payload)
    
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        print("Event:", event)
    except ValueError as e:
        print("ValueError:", e)
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        print("SignatureVerificationError:", e)
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)

    return jsonify(success=True)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        print(f"User ID from session: {user_id}")

        response = users_table.get_item(Key={'id': user_id})
        user = response.get('Item')
        if not user:
            return jsonify({"error": "User not found"})

        print(f"User found: {user}")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=user['email'],
                line_items=[{
                    'price': 'price_1PQOO3Gthr7AaSvU3fHuPOGN',
                }],
                mode='subscription',
                success_url=url_for('subscription_success', _external=True),
                cancel_url=url_for('subscription_cancel', _external=True),
            )

            print(f"Checkout session created: {checkout_session}")

            return jsonify({'checkout_session_id': checkout_session['id']})
        except Exception as e:
            print(f"Error creating checkout session: {str(e)}")
            return jsonify(error=str(e)), 403

    else:
        return render_template('subscribe.html')


@app.route('/subscription_success')
def subscription_success():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        user['user_type'] = 'pro'
        users_table.put_item(Item=user)

    return render_template('subscription_success.html')

@app.route('/subscription_cancel')
def subscription_cancel():
    return render_template('subscription_cancel.html')


@app.route('/change_email', methods=['POST'])
def change_email():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    new_email = request.form['new_email']
    
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')
    
    if user:
        user['email'] = new_email
        users_table.put_item(Item=user)
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route("/feedback", methods=["POST"])
def feedback():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"})

    feedback_text = request.json["feedback"]
    user_id = session['user_id']

    feedback_table.put_item(Item={
        'user_id': user_id,
        'timestamp': str(datetime.utcnow()),
        'feedback': feedback_text
    })

    return jsonify({"message": "Thank you for your feedback!"})


if __name__ == "__main__":
    app.run(debug=True)