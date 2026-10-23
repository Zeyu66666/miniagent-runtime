常见错误
1.
openai.AuthenticationError: Error code: 401 - {'error': {'message': 'Authentication Fails...'}}

`401` = 身份不对 = key 有问题。

2.
openai.APIConnectionError: Connection error.

`APIConnectionError` 是网络问题，不是代码问题

3.
openai.NotFoundError: Error code: 404

`404` = 模型名不存在