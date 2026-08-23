{% snapshot doctors_snapshot %}

{{
    config(
        target_schema='hospital_silver_ven',
        unique_key='doctor_id',
        strategy='check',
        check_cols=[
            'doctor_name',
            'specialization_id',
            'specialization_name',
            'status'
        ]
    )
}}

SELECT *
FROM {{ ref('stg_doctors') }}

{% endsnapshot %}