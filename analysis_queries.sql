-- STRAVA FITNESS DATA ANALYTICS: SQL ANALYSIS

-- 1. Average steps by weekday
SELECT weekday, ROUND(AVG(TotalSteps),0) AS avg_steps
FROM daily_activity
GROUP BY weekday;

-- 2. Activity intensity summary
SELECT ROUND(AVG(LightlyActiveMinutes),1) AS light,
       ROUND(AVG(FairlyActiveMinutes),1) AS fairly,
       ROUND(AVG(VeryActiveMinutes),1) AS very_active,
       ROUND(AVG(SedentaryMinutes),1) AS sedentary
FROM daily_activity;

-- 3. Top active users
SELECT Id, ROUND(AVG(TotalSteps),0) AS avg_daily_steps
FROM daily_activity
GROUP BY Id
ORDER BY avg_daily_steps DESC
LIMIT 10;

-- 4. Most sedentary users
SELECT Id, ROUND(AVG(SedentaryMinutes),1) AS avg_sedentary_minutes
FROM daily_activity
GROUP BY Id
ORDER BY avg_sedentary_minutes DESC
LIMIT 10;

-- 5. Calories by hour
SELECT hour, ROUND(AVG(Calories),2) AS avg_calories
FROM hourly_calories
GROUP BY hour
ORDER BY hour;

-- 6. Sleep summary
SELECT ROUND(AVG(TotalMinutesAsleep),1) AS avg_sleep_minutes,
       ROUND(AVG(TotalTimeInBed),1) AS avg_time_in_bed
FROM sleep_day;
