# WELL
It should work. Lacks some documentation and code cleanup but other than that it is fine I guess.


# Flooter
Flooter is meant as a diff test tool for rest enpoints. Flooter will, according to the configuration, make requests to an endpoint and store the responses as run.
Then to a later date you can repeat the requests and compare the responses with the ones from the previous run. When changes are okay you can accept them to be the new 'main record'.

# Commands
## Run
```SH
flooter --config projct.yaml run
```
Makes a run and shows some information for the run

## List
```SH
flooter --config project.yaml list
```
List all runs.

## Remove
```SH
flooter --config project.yaml rm id
```
Remove a saved run.

## Compare
```SH
flooter --config project.yaml cmp id # compares run with main
flooter --config project.yaml id1 id2 # compares run1 with id2
```
Compares two runs or a run with the main

## Show
```SH
flooter --config project.yaml  show id
flooter --config project.yaml  show main
```
Shows some information to a run

## Accept
```SH
flooter --config project.yaml accept id # accepts an entire run as new main
flooter --config project.yaml accept run_id request_id # accepts an request of a run
```
Accept stuff to main.

# Hooks
A hooks definiton consists of a *source* attribute which is either an
absolute path or a to the config file relative path pointing to a
python file. With that, there can also be up to 8 mappings of a hook
to an callable defined in the source file. The callable is constructed with
the arguments which are defined in the config file.

## Types
### (before/after)_all
The variables dictionary allows storing some sort of information, that
needs to be retained. The variable dictionary is available in every hook
and shared among them.

Signature
```PY
(
  variables: Dict[str, str]
) -> None
```

### (before/after)_testset
Signature
```PY
(
  testset_name: str,
  variables:    Dict[str, str]
) -> None
```

### (before/after)_endpoint
Signature
```PY
(
  testset_name:   str,
  endpoint_name:  str,
  variables:      Dict[str, str]
) -> None
```

### (before/after)_request
The before hook has the ability to make modifications to the parameters,
altough it is not recommended. Also the before hook is called before interpolation and encoding of the parameter takes place.
Signature
```PY
(
  testset_name:   str,
  endpoint_name:  str,
  params:         List[Tuple[str, str]],
  variables:      Dict[str, str]
) -> None
```

## Example
config.yaml
```YAML
hooks:
    source: addons/hooks.py
    before_all:
        use: BeforeAll
        args:
          very_important_kwarg: Hello
          abc: [1, 2, free]
    before_endpoint:
        use: BeforeEndpointHook

```
hooks.py
```PY
# Class definition
class BeforeAllHook:
    def __init__(self, very_important_kwarg: str = 'name', **kwargs):
        print(very_important_kwarg)
        self.kwargs = kwargs
    def __call__(self, variables: Dict[str, Any]):
        variables['test'] = 'endpoint22'

# Closure definition
def BeforeEndpointHook(**kwargs):
  def _inner(testset_name: str, endpoint_name: str, variables: Dict[str, Any]):
    count = variables.get('counter', 0)
    variables['interpolated_var'] = f'Secret-{count}'
    variables.set('counter', count+1)

  return _inner
```

# Transformers
Transformers are a way to alter the response before it is safed. On default, a
response is simply safed but if some information should not be persisted one
can simply define a custom transformer. The transformers configuration requires
a source property which is a absolute path to a python file or to the
config file relative one. Within the names a mapping can be defined from
a within the config file valid name to a in the source file valid callable.
Note: when a transformer is used, it also might make sense to use a custom
comperator as the internal comperators expect the saved object to be of type
requests.Response.

## Transformer signature
```PY
(
  testset_name: str,
  endpoint_name: str,
  response: requests.Response
) -> Any
```

## Example
transformer.py
```PY
def transform_to_lower(testset_name: str,
                       endpoint_name: str,
                       response: requests.Response
                      ) -> requests.Response:
  response._content = response.content.decode('utf-8').lower().strip().encode('utf-8')
  return response
```
config.yaml
```YAML
transformers:
  source: transformers.py
  names:
    simple: transform_to_lower
```


# Comperators
A comperator can be used to compare two responses of any kind which might have been
transformed before. A comperator takes some information together with the two
items to compare. It should return if there were changes and a list of strings
which should be printed out to the screen. The definition in the config file
follows the same rules as the transformers.

## Signature
```PY
(
  testset_name:  str,
  endpoint_name: str,
  request_id:    str,
  a_name:        str,
  a_response:    requests.Response,
  b_name:        str,
  b_response:    requests.Response
) -> Tuple[bool, List[str]]
```

## Example
```PY
def zip_comperator(testset_name:  str,
                   endpoint_name: str,
                   request_id:    str,
                   a_name:        str,
                   a_response:    requests.Response,
                   b_name:        str,
                   b_response:    requests.Response
                  ) -> Tuple[bool, List[str]]:

  has_diff = len(a_response.content) != len(b_response.content)

  return has_diff, 'Has diff' if has_diff else []

def trans_comperator(testset_name:  str,
                     endpoint_name: str,
                     request_id:    str,
                     a_name:        str,
                     a_response:    List[str]],
                     b_name:        str,
                     b_response:    List[str]]
                    ) -> Tuple[bool, List[str]]:
  import difflib

  changes = list(difflib.unified_diff(
            a_response,
            b_response,
            fromfile=a_name,
            tofile=b_name,
            ))
  return len(changes) > 0, changes
```

config.yaml
```YAML
comperators:
  source: /home/bla/comperators.py
  names:
    zipcmp: zip_comperator
    html: trans_comperator
```

## Default comperatator
### Header
Only some header fields are compared which includes: Status-Code, Reason, Content-Type and
Connection

### Body
The comparison is done based on the content type.

#### Text based comparison
Text based content types which includes text and json are compared line wise with a comparison
that most common difftools do. Eg. the diff binary. This comparison is done with difflib
(standard python library).

#### Size based comparison
When the content type of both responses is Zip then the files are compared only by their size

#### Fallback
When the content type of the responses are unknown/unimplemented or the content types are too
different a message is displayed to indicate that problem.



# Strategies
A strategy can be defined in order to create runs for an enpoint.
Each strategy is allowed to receive a dictionary of arguments which
can be defined for every endpoint. The strategy is then supposed to
create a list of runs, where each run consists of tuples which are key
value pairs representing the parameters.

## Signature
```PY
(
  testset_name:   str,
  endpoint_name:  str,
  variables:      Dict[str, Any],
  strategry_args: Dict[str, Union[str, int, float, dict, list]],
  paramters:      List[Parameter]
) -> List[List[Tuple[str, str]]]
```

## Example
```PY
class Parameter:
  values:         List[Any]
  min_occurrence: int
  max_occurrence: int

def generate_some(testset_name:    str,
                endpoint_name:  str,
                variables:      Dict[str, Any],
                strategry_args: Dict[str, Union[str, int, float, dict, list]],
                paramters:      List[Parameter]
               ) -> List[List[Tuple[str, str]]]:
  # static return instead of something done with the actual params just for example
  return [
    [('id', '1')] for _ in range(strategy_args['amount'])
  ]
```

```YAML
strategies:
  source: addons/strats.py
  names:
    some: generate_some

endpoints:
    project/id:
        strategy:
          name: some
          args:
            amount: 2
            b: [1, 2]
```

# Host
The name of the host to make the request to. This can for example be
- wikipedia.org
- localhost:4200
- 192.168.122.2

# Endpoints
...

# Parameters
Parameters are used to make the request and to allow for more flexibility, they can be defined
on three levels. The top level, within a testset and on the endpoint definition itself.
Note, that when overriding a parameter in a deeper level, it is completely overriden and not merged. A parameter can also have an ocurrence count, meaning that a certain parameter might
be required more than once per request. Also writing `{{var_name}}` does a interpolation
from the variable dictionary, that can be altered with hooks.

## Definition
```YAML
parameters:
    nameOfTheParam:
        values: [1, 2, 'test']
    idParam:
        values:
            - '1'
            - '{{var_name}}'
        occurrence:
            min: 2
            max: 3
```

# Testsets
## Hooks
A testset can use other hooks if it wants to. When the same hook
is defined at the top level of the config file and at the testset level the
top level hook will be overshadowed for that testset. For more details, see
the top level hooks description.

```YAML
hooks:
  source: hooks/default.py
  before_all:
    use: default_before_all_hook

testsets:
  tsA:
    hooks:
      source: hooks/special.py
      before_all:
        use: special_before_all_hook
```

# Exit codes
Flooter will exit with code:
- 0: no failure
- 1: cmp failed
- 2: flooter error
- 3: other exceptions


