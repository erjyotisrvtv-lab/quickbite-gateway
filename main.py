import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

UPSTREAMS={
 'catalog': os.environ.get('CATALOG_URL','http://127.0.0.1:3001').rstrip('/'),
 'orders': os.environ.get('ORDERS_URL','http://127.0.0.1:3002').rstrip('/'),
 'deliveries': os.environ.get('DELIVERY_URL','http://127.0.0.1:3003').rstrip('/'),
}
@asynccontextmanager
async def lifespan(app:FastAPI):
    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0),limits=httpx.Limits(max_connections=100,max_keepalive_connections=20)) as client:
        app.state.proxy_client=client
        yield
app=FastAPI(title='QuickBite Food Delivery API Gateway',version='1.0.0',lifespan=lifespan)
STATIC=Path(__file__).parent/'static'
app.mount('/static',StaticFiles(directory=STATIC),name='static')

@app.get('/')
def index():return FileResponse(STATIC/'index.html')
@app.get('/health')
def health():return {'status':'ok','service':'gateway'}
@app.get('/live')
def live():return {'status':'ok'}

@app.api_route('/api/{service}/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE'])
async def proxy(service:str,path:str,request:Request):
    if service not in UPSTREAMS:raise HTTPException(status_code=404,detail='Unknown microservice')
    if not path or '..' in path.split('/'):
        raise HTTPException(status_code=404,detail='Invalid route')
    upstream=f'{UPSTREAMS[service]}/{path}'
    headers={}
    if request.headers.get('content-type'):headers['content-type']=request.headers['content-type']
    try:
        response=await request.app.state.proxy_client.request(
            request.method,upstream,params=list(request.query_params.multi_items()),
            content=await request.body(),headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503,detail=f'{service} service unavailable') from exc
    response_headers={}
    if 'content-type' in response.headers:response_headers['content-type']=response.headers['content-type']
    return Response(content=response.content,status_code=response.status_code,headers=response_headers)
