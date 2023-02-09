import os
import pytest
from firebase_admin import initialize_app, firestore, credentials, auth
from google.cloud.firestore import Client
import requests
from history import DetailedError, firebase_auth, can_log, on_auth_error

def create_user(fs: Client, plan="hobby"):
    # create a user
    user: auth.UserRecord = auth.create_user(
        uid="local",
    )

    # add doc to "links" collection
    fs.collection("links").document().set(
        {
            "token": "local",
            "userId": "local",
        },
        merge=True,
    )

    auth.set_custom_user_claims(user.uid, {"stripeRole": plan})


def delete_user(fs: Client):
    # delete user
    auth.delete_user("local")
    docs = fs.collection("links").where("userId", "==", "local").get()
    docs = docs + fs.collection("history").where("user", "==", "local").get()
    docs = docs + [fs.collection("quotas").document("local").get()]
    batch = fs.batch()
    for i, doc in enumerate(docs):
        batch.delete(doc.reference)
        if i % 400 == 0:
            batch.commit()
            batch = fs.batch()
    batch.commit()

# TODO update tests outdated with auth etc
@pytest.fixture(autouse=True)
def run_around_tests():
    # ignore in ci/cd as firebase emulator does not work there yet
    if os.environ.get("IS_CI_CD") == "true":
        yield
        return
    # set in env
    # FIRESTORE_EMULATOR_HOST="localhost:8080"
    # FIREBASE_AUTH_EMULATOR_HOST="localhost:9099"
    # os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    # os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = "localhost:9099"
    # npx firebase emulators:start --only firestore,auth

    # TODO: kinda does not work / broken - use bash
    # process = subprocess.Popen(
    #     ["npx", "firebase", "emulators:start", "--only", "firestore,auth"],
    #     stdout=subprocess.PIPE,
    # )
    # process.communicate()
    # wait until "All emulators ready!" is printed to stdout
    # while True:
    #     line = process.stdout.readline()
    #     line_as_str = line.decode("utf-8")
    #     if line_as_str in "All emulators ready":
    #         break
    #     time.sleep(0.1)
    # time.sleep(5) # HACK
    try:
        cred = credentials.Certificate("svc.prod.json")
        initialize_app(cred)
    except Exception as e:
        print(e)

    yield

    delete_user(firestore.client())
    # time.sleep(1)
    # process.kill()
    # kill all processes on port 9099, 8080, 5000
    # subprocess.run(["npx", "kill-port", "9099", "8080", "5000", "4000"])


def test_search():
    create_user(firestore.client(), plan="admin")
    response = requests.post(
        "http://localhost:8000/v1/dev/search",
        json={
            "query": "Bob",
        },
        headers={
            "Authorization": "Bearer local",
        },
        timeout=10,
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["query"] == "Bob"
    assert "similarities" in json_data
    # {'query': 'Bob', 'similarities': [...]}

# def test_text_create_properly_forward_openai_error():
#     try:
#         create_user(firestore.client(), plan="admin")
#     except Exception as e:
#         print(e)

#     response = client.post(
#         "/v1/text/create",
#         json={
#             "model": "adaa", # wrong model
#             "prompt": "1",
#         },
#         headers={
#             "Authorization": "Bearer local",
#         },
#     )
#     assert response.status_code == 200
#     e = "data: {'error': 'We are facing issues with our AI provider. Please try again later.'}\r\n\r\n"
#     assert response.text == e, f"got {response.text}"



# def test_history_middleware():
#     _firestore = firestore.client()
#     response = client.post(
#         "/v1/text/create",
#         json={
#             "model": "ada",
#             "prompt": "1 + 1 =",
#             "stop": ["\n"],
#         },
#         headers={
#             "Authorization": "Bearer local",
#         },
#     )
#     assert response.status_code == 200

#     # check a history document is created with my ip address recently ("local" when dev)
#     query = _firestore.collection("history").where("user", "==", "local")
#     # TODO: does not work IDK why; somehow how I query date does not work
#     # max 30 seconds ago
#     # from datetime import datetime, timedelta
#     # thirty_seconds_ago = datetime.now() - timedelta(seconds=30)
#     # query = query.where("timestamp", ">", thirty_seconds_ago)
#     history_docs = query.get()
#     assert len(history_docs) > 0
#     # clean collection from "local" user
#     batch = _firestore.batch()
#     for doc in history_docs:
#         batch.delete(doc.reference)
#     batch.commit()


# def test_local_emulator():
#     _firestore = firestore.client()
#     _firestore.collection("foos").document().set(
#         {
#             "foo": "bar",
#         },
#         merge=True,
#     )
#     docs = _firestore.collection("foos").get()
#     assert len(docs) > 0, "No documents found"
#     # cleanup
#     batch = _firestore.batch()
#     for doc in docs:
#         batch.delete(doc.reference)
#     batch.commit()


# def test_history_within_plan(images = 200, texts = 900):
#     if os.environ.get("IS_CI_CD") == "true":
#         return
#     _firestore = firestore.client()

#     # a bunch of fake history documents
#     batch = _firestore.batch()
#     for _ in range(images + 1):
#         batch.set(
#             _firestore.collection("history").document(),
#             {
#                 "user": "local",
#                 "group": "default",
#                 "timestamp": firestore.SERVER_TIMESTAMP,
#                 "scope": {
#                     "path": "/v1/image/create",
#                 },
#             },
#         )
#     batch.commit()
#     batch = _firestore.batch()
#     for i in range(texts):
#         batch.set(
#             _firestore.collection("history").document(),
#             {
#                 "user": "local",
#                 "group": "default",
#                 "timestamp": firestore.SERVER_TIMESTAMP,
#                 "scope": {
#                     "path": "/v1/text/create",
#                 },
#             },
#         )
#         if i % 100 == 0:
#             batch.commit()
#             batch = _firestore.batch()
#     batch.commit()
#     response = client.post(
#         "/v1/image/create",
#         json={
#             "size": 512,
#             "limit": 1,
#             "prompt": "A group of Giraffes visiting a zoo on mars populated by humans",
#         },
#         headers={
#             "Authorization": "Bearer local",
#         },
#     )
#     assert response.status_code == 402
#     response = client.post(
#         "/v1/text/create",
#         json={
#             "prompt": "A group of Giraffes visiting a zoo on mars populated by humans",
#             "model": "text-davinci-003",
#         },
#         headers={
#             "Authorization": "Bearer local",
#         },
#     )
#     assert response.status_code == 200

# def test_history_within_plan_hobby():
#     test_history_within_plan()

# def test_history_within_plan_free():
#     auth.set_custom_user_claims("local", {"stripe_role": "free"})
#     test_history_within_plan(10, 1)
    

@pytest.mark.asyncio
async def test_firebase_auth():
    create_user(firestore.client(), plan="admin")
    scope = {}
    scope["headers"] = {"authorization": "Bearer local"}
    uid, group = await firebase_auth(scope)
    assert uid == "local"
    assert group == "default"
    assert scope["uid"] == "local"
    assert scope["group"] == "default"
    assert scope["stripe_role"] == "free"

@pytest.mark.asyncio
async def test_firestore_can_log():
    create_user(firestore.client(), plan="admin")
    scope = {}
    scope["headers"] = ("authorization", "Bearer local")
    error = await can_log("local", "default", scope)
    assert error is None

@pytest.mark.asyncio
async def test_on_auth_error():
    create_user(firestore.client(), plan="admin")
    scope = {}
    e = DetailedError(scope, 401, str("foobar"))
    result = await on_auth_error(e, scope)
    assert result.status_code == 401
    import json
    body = json.loads(result.body.decode("utf-8"))
    assert body == {"message": "foobar"}
    e = Exception("foobar")
    result = await on_auth_error(e, scope)
    assert result.status_code == 500
    body = json.loads(result.body.decode("utf-8"))
    assert body == {"message": "foobar"}
