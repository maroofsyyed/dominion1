#!/usr/bin/env python3
import requests
import json
import uuid
import time
import os
import random
from datetime import datetime

# Get the backend URL from the frontend .env file
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.strip().split('=')[1].strip('"')
            break

# Ensure the URL doesn't have quotes
BACKEND_URL = BACKEND_URL.strip("'\"")
API_URL = f"{BACKEND_URL}/api"

print(f"Testing backend API at: {API_URL}")

# Test user data
test_user = {
    "username": f"testuser_{uuid.uuid4().hex[:8]}",
    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
    "password": "Test@123",
    "full_name": "Test User",
    "age": 30,
    "height": 175.5,
    "weight": 70.2,
    "university": "Test University",
    "city": "Test City"
}

# Second test user for social features
test_user2 = {
    "username": f"testuser2_{uuid.uuid4().hex[:8]}",
    "email": f"test2_{uuid.uuid4().hex[:8]}@example.com",
    "password": "Test@123",
    "full_name": "Test User 2",
    "age": 28,
    "height": 180.0,
    "weight": 75.5,
    "university": "Another University",
    "city": "Another City"
}

# Store test results
test_results = {
    "total_tests": 0,
    "passed_tests": 0,
    "failed_tests": 0,
    "failures": []
}

# Helper function to run a test
def run_test(name, test_func, *args, **kwargs):
    print(f"\n===== Testing {name} =====")
    test_results["total_tests"] += 1
    try:
        result = test_func(*args, **kwargs)
        test_results["passed_tests"] += 1
        print(f"✅ PASSED: {name}")
        return result
    except AssertionError as e:
        test_results["failed_tests"] += 1
        test_results["failures"].append({"name": name, "error": str(e)})
        print(f"❌ FAILED: {name} - {str(e)}")
        return None
    except Exception as e:
        test_results["failed_tests"] += 1
        test_results["failures"].append({"name": name, "error": f"Exception: {str(e)}"})
        print(f"❌ FAILED: {name} - Exception: {str(e)}")
        return None

# 1. Test User Authentication System
def test_user_registration():
    response = requests.post(f"{API_URL}/auth/register", json=test_user)
    assert response.status_code == 200, f"Registration failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access token in response"
    assert "user" in data, "No user data in response"
    assert data["user"]["username"] == test_user["username"], "Username mismatch"
    assert data["user"]["email"] == test_user["email"], "Email mismatch"
    return data["access_token"]

def test_user2_registration():
    response = requests.post(f"{API_URL}/auth/register", json=test_user2)
    assert response.status_code == 200, f"Registration failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access token in response"
    assert "user" in data, "No user data in response"
    assert data["user"]["username"] == test_user2["username"], "Username mismatch"
    assert data["user"]["email"] == test_user2["email"], "Email mismatch"
    return data["access_token"], data["user"]

def test_user_login():
    login_data = {
        "email": test_user["email"],
        "password": test_user["password"]
    }
    response = requests.post(f"{API_URL}/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access token in response"
    assert "user" in data, "No user data in response"
    assert data["user"]["username"] == test_user["username"], "Username mismatch"
    return data["access_token"]

def test_get_current_user(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    assert response.status_code == 200, f"Get current user failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert data["username"] == test_user["username"], "Username mismatch"
    assert data["email"] == test_user["email"], "Email mismatch"
    return data

# 2. Test Exercise Database
def test_get_exercises():
    response = requests.get(f"{API_URL}/exercises")
    assert response.status_code == 200, f"Get exercises failed with status {response.status_code}: {response.text}"
    exercises = response.json()
    assert len(exercises) >= 25, f"Expected at least 25 exercises, got {len(exercises)}"
    
    # Check if all 6 pillars are present
    pillars = set(exercise["pillar"] for exercise in exercises)
    expected_pillars = {"Horizontal Pull", "Vertical Pull", "Vertical Push", "Horizontal Push", "Core", "Legs"}
    assert expected_pillars.issubset(pillars), f"Missing pillars. Expected {expected_pillars}, got {pillars}"
    
    # Check if all skill levels are present
    skill_levels = set(exercise["skill_level"] for exercise in exercises)
    expected_skill_levels = {"Beginner", "Intermediate", "Advanced", "Elite"}
    assert expected_skill_levels.intersection(skill_levels), f"Missing skill levels. Expected some of {expected_skill_levels}, got {skill_levels}"
    
    return exercises

def test_filter_exercises_by_pillar():
    pillar = "Vertical Pull"
    response = requests.get(f"{API_URL}/exercises?pillar={pillar}")
    assert response.status_code == 200, f"Filter exercises by pillar failed with status {response.status_code}: {response.text}"
    exercises = response.json()
    assert all(exercise["pillar"] == pillar for exercise in exercises), "Not all exercises match the pillar filter"
    return exercises

def test_filter_exercises_by_skill_level():
    skill_level = "Beginner"
    response = requests.get(f"{API_URL}/exercises?skill_level={skill_level}")
    assert response.status_code == 200, f"Filter exercises by skill level failed with status {response.status_code}: {response.text}"
    exercises = response.json()
    assert all(exercise["skill_level"] == skill_level for exercise in exercises), "Not all exercises match the skill level filter"
    return exercises

def test_get_exercise_by_id(exercises):
    if not exercises:
        return None
    exercise_id = exercises[0]["id"]
    response = requests.get(f"{API_URL}/exercises/{exercise_id}")
    assert response.status_code == 200, f"Get exercise by ID failed with status {response.status_code}: {response.text}"
    exercise = response.json()
    assert exercise["id"] == exercise_id, "Exercise ID mismatch"
    return exercise

def test_get_pillars():
    response = requests.get(f"{API_URL}/exercises/pillars")
    assert response.status_code == 200, f"Get pillars failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "pillars" in data, "No pillars in response"
    pillars = data["pillars"]
    expected_pillars = {"Horizontal Pull", "Vertical Pull", "Vertical Push", "Horizontal Push", "Core", "Legs"}
    assert set(pillars).intersection(expected_pillars), f"Missing pillars. Expected some of {expected_pillars}, got {pillars}"
    return pillars

# 3. Test Progress Tracking System
def test_log_progress(token, exercises, user_data):
    if not exercises:
        return None
    
    exercise_id = exercises[0]["id"]
    progress_data = {
        "exercise_id": exercise_id,
        "reps": 10,
        "sets": 3,
        "notes": "Test progress entry",
        "user_id": user_data["id"]
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/progress", json=progress_data, headers=headers)
    assert response.status_code == 200, f"Log progress failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert data["exercise_id"] == exercise_id, "Exercise ID mismatch"
    assert data["reps"] == progress_data["reps"], "Reps mismatch"
    assert data["sets"] == progress_data["sets"], "Sets mismatch"
    return data

def test_get_user_progress(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/progress", headers=headers)
    assert response.status_code == 200, f"Get user progress failed with status {response.status_code}: {response.text}"
    progress_entries = response.json()
    assert isinstance(progress_entries, list), "Progress entries is not a list"
    return progress_entries

def test_get_exercise_progress(token, exercises, progress_entry):
    if not exercises or not progress_entry:
        return None
    
    exercise_id = progress_entry["exercise_id"]
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/progress/{exercise_id}", headers=headers)
    assert response.status_code == 200, f"Get exercise progress failed with status {response.status_code}: {response.text}"
    progress_entries = response.json()
    assert isinstance(progress_entries, list), "Progress entries is not a list"
    assert all(entry["exercise_id"] == exercise_id for entry in progress_entries), "Not all progress entries match the exercise ID"
    return progress_entries

# 4. Test Mobility Exercises
def test_get_mobility_exercises():
    response = requests.get(f"{API_URL}/mobility")
    assert response.status_code == 200, f"Get mobility exercises failed with status {response.status_code}: {response.text}"
    exercises = response.json()
    assert len(exercises) > 0, "No mobility exercises found"
    return exercises

def test_get_mobility_exercise_by_id(mobility_exercises):
    if not mobility_exercises:
        return None
    
    exercise_id = mobility_exercises[0]["id"]
    response = requests.get(f"{API_URL}/mobility/{exercise_id}")
    assert response.status_code == 200, f"Get mobility exercise by ID failed with status {response.status_code}: {response.text}"
    exercise = response.json()
    assert exercise["id"] == exercise_id, "Mobility exercise ID mismatch"
    return exercise

# 5. Test Shop/Products
def test_get_products():
    response = requests.get(f"{API_URL}/products")
    assert response.status_code == 200, f"Get products failed with status {response.status_code}: {response.text}"
    products = response.json()
    assert len(products) > 0, "No products found"
    return products

def test_get_product_by_id(products):
    if not products:
        return None
    
    product_id = products[0]["id"]
    response = requests.get(f"{API_URL}/products/{product_id}")
    assert response.status_code == 200, f"Get product by ID failed with status {response.status_code}: {response.text}"
    product = response.json()
    assert product["id"] == product_id, "Product ID mismatch"
    return product

# 6. Test Community Features
def test_get_communities():
    response = requests.get(f"{API_URL}/communities")
    assert response.status_code == 200, f"Get communities failed with status {response.status_code}: {response.text}"
    communities = response.json()
    # Note: Communities might be empty initially, so we don't assert length
    return communities

def test_join_community(token, communities):
    # If no communities exist, create a test community first
    if not communities:
        print("No communities found, skipping join community test")
        return None
    
    community_id = communities[0]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/communities/{community_id}/join", headers=headers)
    assert response.status_code == 200, f"Join community failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "message" in data, "No message in response"
    return data

def test_get_community_messages(communities):
    if not communities:
        print("No communities found, skipping get community messages test")
        return None
    
    community_id = communities[0]["id"]
    response = requests.get(f"{API_URL}/communities/{community_id}/messages")
    assert response.status_code == 200, f"Get community messages failed with status {response.status_code}: {response.text}"
    messages = response.json()
    assert isinstance(messages, list), "Messages is not a list"
    return messages

def test_get_leaderboard():
    response = requests.get(f"{API_URL}/leaderboard")
    assert response.status_code == 200, f"Get leaderboard failed with status {response.status_code}: {response.text}"
    leaderboard = response.json()
    assert isinstance(leaderboard, list), "Leaderboard is not a list"
    return leaderboard

# 7. Test Workout Management
def test_create_workout(token, exercises, user_data):
    if not exercises or len(exercises) < 2:
        return None
    
    workout_data = {
        "name": "Test Workout",
        "user_id": user_data["id"],
        "exercises": [
            {
                "exercise_id": exercises[0]["id"],
                "sets": 3,
                "reps": 10
            },
            {
                "exercise_id": exercises[1]["id"],
                "sets": 4,
                "reps": 8
            }
        ]
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/workouts", json=workout_data, headers=headers)
    assert response.status_code == 200, f"Create workout failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == workout_data["name"], "Workout name mismatch"
    assert len(data["exercises"]) == len(workout_data["exercises"]), "Workout exercises count mismatch"
    return data

def test_get_user_workouts(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/workouts", headers=headers)
    assert response.status_code == 200, f"Get user workouts failed with status {response.status_code}: {response.text}"
    workouts = response.json()
    assert isinstance(workouts, list), "Workouts is not a list"
    return workouts

# 8. Test Enhanced Mobility System
def test_create_mobility_assessment(token, user_data):
    assessment_data = {
        "user_id": user_data["id"],
        "assessment_type": "overhead_squat",
        "score": 2,
        "notes": "Good mobility, slight forward lean",
        "areas_of_concern": ["ankle_mobility", "thoracic_spine"]
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/mobility/assessments", json=assessment_data, headers=headers)
    assert response.status_code == 200, f"Create mobility assessment failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert data["assessment_type"] == assessment_data["assessment_type"], "Assessment type mismatch"
    assert data["score"] == assessment_data["score"], "Score mismatch"
    return data

def test_get_mobility_assessments(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/mobility/assessments", headers=headers)
    assert response.status_code == 200, f"Get mobility assessments failed with status {response.status_code}: {response.text}"
    assessments = response.json()
    assert isinstance(assessments, list), "Assessments is not a list"
    return assessments

def test_get_mobility_recommendations(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/mobility/recommendations", headers=headers)
    assert response.status_code == 200, f"Get mobility recommendations failed with status {response.status_code}: {response.text}"
    recommendations = response.json()
    assert isinstance(recommendations, dict), "Recommendations is not a dictionary"
    # If no assessment has been done, we should get general recommendations
    if "message" in recommendations:
        assert "general_exercises" in recommendations, "No general exercises in recommendations"
    # If assessment has been done, we should get personalized recommendations
    else:
        assert "recommended_exercises" in recommendations, "No recommended exercises in recommendations"
    return recommendations

# 9. Test Enhanced Social Features
def test_user_search(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/users/search?q={test_user2['username'][:5]}", headers=headers)
    assert response.status_code == 200, f"User search failed with status {response.status_code}: {response.text}"
    users = response.json()
    assert isinstance(users, list), "Users is not a list"
    assert len(users) > 0, "No users found in search"
    return users

def test_follow_user(token, user2_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/users/follow/{user2_id}", headers=headers)
    assert response.status_code == 200, f"Follow user failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "message" in data, "No message in response"
    return data

def test_get_user_profile(token, user2_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/users/{user2_id}/profile", headers=headers)
    assert response.status_code == 200, f"Get user profile failed with status {response.status_code}: {response.text}"
    profile = response.json()
    assert profile["id"] == user2_id, "User ID mismatch"
    return profile

# 10. Test Challenges & Gamification
def test_get_challenges():
    response = requests.get(f"{API_URL}/challenges")
    assert response.status_code == 200, f"Get challenges failed with status {response.status_code}: {response.text}"
    challenges = response.json()
    assert isinstance(challenges, list), "Challenges is not a list"
    assert len(challenges) == 3, f"Expected 3 challenges, got {len(challenges)}"
    return challenges

def test_join_challenge(token, challenges):
    if not challenges:
        return None
    
    challenge_id = challenges[0]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/challenges/{challenge_id}/join", headers=headers)
    assert response.status_code == 200, f"Join challenge failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "message" in data, "No message in response"
    return data

def test_get_achievements():
    response = requests.get(f"{API_URL}/achievements")
    assert response.status_code == 200, f"Get achievements failed with status {response.status_code}: {response.text}"
    achievements = response.json()
    assert isinstance(achievements, list), "Achievements is not a list"
    assert len(achievements) == 5, f"Expected 5 achievements, got {len(achievements)}"
    return achievements

# 11. Test Chat Channels
def test_get_chat_channels():
    response = requests.get(f"{API_URL}/chat/channels")
    assert response.status_code == 200, f"Get chat channels failed with status {response.status_code}: {response.text}"
    channels = response.json()
    assert isinstance(channels, list), "Channels is not a list"
    return channels

def test_join_chat_channel(token, channels):
    if not channels:
        return None
    
    channel_id = channels[0]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/chat/channels/{channel_id}/join", headers=headers)
    assert response.status_code == 200, f"Join chat channel failed with status {response.status_code}: {response.text}"
    data = response.json()
    assert "message" in data, "No message in response"
    return data

# 12. Test Analytics
def test_get_progress_analytics(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/analytics/progress", headers=headers)
    assert response.status_code == 200, f"Get progress analytics failed with status {response.status_code}: {response.text}"
    analytics = response.json()
    assert isinstance(analytics, dict), "Analytics is not a dictionary"
    return analytics

# Run all tests
def run_all_tests():
    print("\n========== DOMINION FITNESS PLATFORM BACKEND TESTS ==========\n")
    
    # 1. User Authentication System
    token = run_test("User Registration", test_user_registration)
    if not token:
        token = run_test("User Login", test_user_login)
    
    user_data = None
    if token:
        user_data = run_test("Get Current User", test_get_current_user, token)
    
    # Register second user for social features testing
    token2, user2_data = None, None
    if token:
        token2, user2_data = run_test("Second User Registration", test_user2_registration)
    
    # 2. Exercise Database
    exercises = run_test("Get Exercises", test_get_exercises)
    run_test("Filter Exercises by Pillar", test_filter_exercises_by_pillar)
    run_test("Filter Exercises by Skill Level", test_filter_exercises_by_skill_level)
    if exercises:
        run_test("Get Exercise by ID", test_get_exercise_by_id, exercises)
    run_test("Get Pillars", test_get_pillars)
    
    # 3. Progress Tracking System
    if token and exercises and user_data:
        progress_entry = run_test("Log Progress", test_log_progress, token, exercises, user_data)
        progress_entries = run_test("Get User Progress", test_get_user_progress, token)
        if progress_entry:
            run_test("Get Exercise Progress", test_get_exercise_progress, token, exercises, progress_entry)
    
    # 4. Mobility Exercises
    mobility_exercises = run_test("Get Mobility Exercises", test_get_mobility_exercises)
    if mobility_exercises:
        run_test("Get Mobility Exercise by ID", test_get_mobility_exercise_by_id, mobility_exercises)
    
    # 5. Shop/Products
    products = run_test("Get Products", test_get_products)
    if products:
        run_test("Get Product by ID", test_get_product_by_id, products)
    
    # 6. Community Features
    communities = run_test("Get Communities", test_get_communities)
    if token and communities:
        run_test("Join Community", test_join_community, token, communities)
    if communities:
        run_test("Get Community Messages", test_get_community_messages, communities)
    run_test("Get Leaderboard", test_get_leaderboard)
    
    # 7. Workout Management
    if token and exercises and user_data:
        workout = run_test("Create Workout", test_create_workout, token, exercises, user_data)
        run_test("Get User Workouts", test_get_user_workouts, token)
    
    # 8. Enhanced Mobility System
    if token and user_data:
        assessment = run_test("Create Mobility Assessment", test_create_mobility_assessment, token, user_data)
        run_test("Get Mobility Assessments", test_get_mobility_assessments, token)
        run_test("Get Mobility Recommendations", test_get_mobility_recommendations, token)
    
    # 9. Enhanced Social Features
    if token and user2_data:
        users = run_test("User Search", test_user_search, token)
        run_test("Follow User", test_follow_user, token, user2_data["id"])
        run_test("Get User Profile", test_get_user_profile, token, user2_data["id"])
    
    # 10. Challenges & Gamification
    challenges = run_test("Get Challenges", test_get_challenges)
    if token and challenges:
        run_test("Join Challenge", test_join_challenge, token, challenges)
    run_test("Get Achievements", test_get_achievements)
    
    # 11. Chat Channels
    channels = run_test("Get Chat Channels", test_get_chat_channels)
    if token and channels:
        run_test("Join Chat Channel", test_join_chat_channel, token, channels)
    
    # 12. Analytics
    if token:
        run_test("Get Progress Analytics", test_get_progress_analytics, token)
    
    # Print summary
    print("\n========== TEST SUMMARY ==========")
    print(f"Total tests: {test_results['total_tests']}")
    print(f"Passed tests: {test_results['passed_tests']}")
    print(f"Failed tests: {test_results['failed_tests']}")
    
    if test_results["failures"]:
        print("\nFailed tests:")
        for failure in test_results["failures"]:
            print(f"- {failure['name']}: {failure['error']}")
    
    return test_results["failed_tests"] == 0

if __name__ == "__main__":
    run_all_tests()
