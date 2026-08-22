SELECT
    d.department_id,
    d.department_name,
    COUNT(a.admission_id) AS admission_count
FROM {{ ref('stg_departments') }} AS d
LEFT JOIN {{ ref('stg_admissions') }} AS a
    ON d.department_id = a.department_id
GROUP BY
    d.department_id,
    d.department_name
ORDER BY
    admission_count DESC