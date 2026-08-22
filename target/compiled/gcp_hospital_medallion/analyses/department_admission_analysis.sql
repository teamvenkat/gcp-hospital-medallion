SELECT
    d.department_id,
    d.department_name,
    COUNT(a.admission_id) AS admission_count
FROM `project-5fbc8bf7-2dd6-4f0a-a5f`.`hospital_silver`.`stg_departments` AS d
LEFT JOIN `project-5fbc8bf7-2dd6-4f0a-a5f`.`hospital_silver`.`stg_admissions` AS a
    ON d.department_id = a.department_id
GROUP BY
    d.department_id,
    d.department_name
ORDER BY
    admission_count DESC