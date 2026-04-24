from aiogram import BaseMiddleware


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tg_user = data.get("event_from_user")

        if not tg_user:
            return await handler(event, data)
        
        services = data['services']
        user = await services.user_service().get_or_create(tg_user)
        data['user'] = user
        return await handler(event, data)