import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CarMake, CarModel
from .populate import initiate
from .restapis import analyze_review_sentiments, get_request, post_review


logger = logging.getLogger(__name__)


# Create a `login_user` view to handle sign-in request
@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    username = data["userName"]
    password = data["password"]

    user = authenticate(username=username, password=password)

    response_data = {"userName": username}

    if user is not None:
        login(request, user)
        response_data = {
            "userName": username,
            "status": "Authenticated",
        }

    return JsonResponse(response_data)


# Create a `logout_request` view to handle sign-out request
def logout_request(request):
    logout(request)
    data = {"userName": ""}
    return JsonResponse(data)


# Create a `registration` view to handle sign-up request
@csrf_exempt
def registration(request):
    data = json.loads(request.body)

    username = data["userName"]
    password = data["password"]
    first_name = data["firstName"]
    last_name = data["lastName"]
    email = data["email"]

    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {"error": "Username already exists"},
            status=400,
        )

    # Create user
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    # Login user
    login(request, user)

    return JsonResponse(
        {
            "userName": username,
            "status": "Authenticated",
        }
    )


def get_cars(request):
    count = CarMake.objects.count()

    if count == 0:
        initiate()

    car_models = CarModel.objects.select_related("car_make")
    cars = []

    for car_model in car_models:
        cars.append(
            {
                "CarModel": car_model.name,
                "CarMake": car_model.car_make.name,
            }
        )

    return JsonResponse({"CarModels": cars})


# Update the `get_dealerships` render list of dealerships
def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = f"/fetchDealers/{state}"

    dealerships = get_request(endpoint)

    return JsonResponse(
        {
            "status": 200,
            "dealers": dealerships,
        }
    )


# Create a `get_dealer_reviews` view to render the reviews of a dealer
def get_dealer_reviews(request, dealer_id):
    if dealer_id:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint)

        for review_detail in reviews:
            sentiment_response = analyze_review_sentiments(
                review_detail["review"]
            )

            if sentiment_response and "sentiment" in sentiment_response:
                review_detail["sentiment"] = sentiment_response["sentiment"]
            else:
                review_detail["sentiment"] = "neutral"

        return JsonResponse(
            {
                "status": 200,
                "reviews": reviews,
            }
        )

    return JsonResponse(
        {
            "status": 400,
            "message": "Bad Request",
        }
    )


# Create a `get_dealer_details` view to render the dealer details
def get_dealer_details(request, dealer_id):
    if dealer_id:
        endpoint = f"/fetchDealer/{dealer_id}"
        dealership = get_request(endpoint)

        return JsonResponse(
            {
                "status": 200,
                "dealer": dealership,
            }
        )

    return JsonResponse(
        {
            "status": 400,
            "message": "Bad Request",
        }
    )


# Create an `add_review` view to submit a review
def add_review(request):
    if not request.user.is_anonymous:
        data = json.loads(request.body)

        try:
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse(
                {
                    "status": 401,
                    "message": "Error in posting review",
                }
            )

    return JsonResponse(
        {
            "status": 403,
            "message": "Unauthorized",
        }
    )
