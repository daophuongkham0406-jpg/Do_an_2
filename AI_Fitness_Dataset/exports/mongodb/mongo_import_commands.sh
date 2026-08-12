#!/usr/bin/env bash
mongoimport --db ai_fitness --collection users --file users.json --jsonArray
mongoimport --db ai_fitness --collection exercises --file exercises.json --jsonArray
mongoimport --db ai_fitness --collection workout_plans --file workout_plans.json --jsonArray
mongoimport --db ai_fitness --collection workout_history --file workout_history.json --jsonArray
mongoimport --db ai_fitness --collection user_feedback --file user_feedback.json --jsonArray
