# AI-Based Predictive Maintenance System for Induction Motors

## Project Overview

This project focuses on the design and implementation of an AI-based predictive maintenance system for induction motors using IoT sensors.

The system collects motor condition data, including temperature, current, and vibration. The collected data is processed and analyzed using machine learning to identify abnormal motor conditions and support early fault detection.

## Objectives

- Collect induction motor condition data using IoT sensors.
- Develop a supervised machine learning model for motor condition classification.
- Use an ESP32-based sensor system to collect and validate motor data.
- Develop a real-time dashboard for monitoring motor condition and predictions.

## Technologies Used

- Python
- Scikit-learn
- Random Forest
- ESP32
- Temperature Sensor
- Current Sensor
- Vibration Sensor
- Django
- React
- Git & GitHub

## Machine Learning Model

The project uses a **Random Forest classification model** to classify motor conditions based on:

- Temperature
- Current
- Vibration

The model is evaluated using:

- Accuracy
- Precision
- Recall
- F1-score

## System Workflow

```text
Temperature Sensor ─┐
Current Sensor ─────┼──> ESP32 ──> Data Processing ──> ML Model
Vibration Sensor ───┘                                      │
                                                           ↓
                                                      Prediction
                                                           │
                                                           ↓
                                                       Dashboard