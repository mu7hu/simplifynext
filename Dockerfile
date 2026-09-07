FROM public.ecr.aws/lambda/python:3.12

COPY requirements-lambda.txt ${LAMBDA_TASK_ROOT}/requirements-lambda.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-lambda.txt --target ${LAMBDA_TASK_ROOT}

COPY src ${LAMBDA_TASK_ROOT}/src
COPY data ${LAMBDA_TASK_ROOT}/data

ENV PYTHONPATH=${LAMBDA_TASK_ROOT}/src

# SAM overrides this command for the Analyst and Content functions.
CMD ["traction.api.run_cycle_lambda.handler"]
