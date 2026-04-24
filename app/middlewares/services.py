from aiogram import BaseMiddleware
from services.factory import ServiceFactory


class ServiceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session = data['session']
        data['services'] = ServiceFactory(session)
        return await handler(event, data)