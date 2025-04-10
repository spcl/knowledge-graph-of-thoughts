# Python Execution

The execution of Python code is implemented as a [Flask](https://github.com/pallets/flask) application.

## API URLs

A call to the API URLs always returns a JSON dictionary and a status code.
The dictionary for errors uses the following structure:

```python
{
    "error": str
}
```

### Execute Python Code

A POST call to "/run" executes the supplied Python code in an environment with the supplied Python packages.

The input JSON data structure supports the following fields:

```python
{
   "required_modules": list[str], # List of packages to install.
   "code": str # Python code to run.
}
```

Potential status codes for errors are 400 and 408.
The resulting JSON data structure has the following format with the status code being 200:

```python
{
    "output": str # Output of the code execution.
}
```
