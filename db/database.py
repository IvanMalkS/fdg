import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import inspect, select
import os
import pandas as pd
from db.models import AiCreators, Models, AiSettings
from services.logger import logger
from db.base import Base
from config import Config

def get_db_url():
    return (
        f"postgresql+asyncpg://"
        f"{Config.DB_USER}:{Config.DB_PASSWORD}@"
        f"{Config.DB_HOST}:{Config.DB_PORT}/"
        f"{Config.DB_NAME}"
    )

engine = create_async_engine(get_db_url())

async def init_db():
    async with engine.begin() as conn:
        if Config.DROP_DB_ON_STARTUP:
            logger.info("Clear DB")
            await conn.run_sync(Base.metadata.drop_all)

        await conn.run_sync(Base.metadata.create_all)

        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

        logger.info(f"Tables {', '.join(tables)} created")

    await load_data_from_excel()

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        await create_defaults_settings(session)
    logger.info("PG DB started successfully")
    return engine


async def load_data_from_excel():
    try:
        excel_dir = os.path.join(os.getcwd(), 'excel')
        dfs = {
            'dama_competencies': pd.read_excel(os.path.join(excel_dir, "dama_competencies.xlsx")),
            'dama_questions': pd.read_excel(os.path.join(excel_dir, "dama_questions.xlsx")),
            'dama_cases': pd.read_excel(os.path.join(excel_dir, "dama_cases.xlsx")),
            'dama_roles': pd.read_excel(os.path.join(excel_dir, "dama_roles.xlsx"))
        }

        async with engine.begin() as conn:
            for table_name, df in dfs.items():
                df.columns = df.columns.str.lower()

                await conn.run_sync(
                    lambda sync_conn: df.to_sql(
                        table_name.lower(),
                        sync_conn,
                        if_exists='append',
                        index=False,
                        method='multi'
                    )
                )

        logger.info("Data load from EXCEL")
    except Exception as e:
        logger.error(f"Error while loading from EXCEL: {e}")
        raise


async def load_new_provider(creator: str, token: str, url: str):
    try:
        async_session = get_async_session()

        async with async_session as session:
            async with session.begin():
                result = await session.execute(
                    select(AiCreators).where(AiCreators.name == creator)
                )
                ai_creator = result.scalar_one_or_none()

                if not ai_creator:
                    new_creator = AiCreators(name=creator, token=token, url=url)
                    session.add(new_creator)
                    logger.info(f"Created new provider {creator}")

    except Exception as e:
        logger.error(f"Error while creation new provider {creator}: {e}")


async def load_models(models_link: str, token: str, creator_id: int):
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(models_link, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error while load models: {response.status} - {error_text}")
                    raise Exception(f"API error {response.status}: {error_text}")

                data = await response.json()

                if "data" not in data:
                    logger.error(f"Invalid API response format: {data}")
                    raise Exception("Invalid API response format")

                models = data["data"]
                if not models:
                    logger.info(data)
                    logger.warning("Empty models list")
                    return False

        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            async with session.begin():
                creator = await session.get(AiCreators, creator_id)

                if not creator:
                    logger.error(f'Создатель с ID {creator_id} не найден')
                    return False

                added_models = 0
                for model_data in models:
                    if "imagen" in model_data["id"].lower():
                        continue

                    model_name = model_data["id"]
                    if model_name.startswith("models/"):
                        model_name = model_name[7:]

                    model = Models(
                        name=model_name,
                        ai_creator_id=int(creator_id)
                    )
                    session.add(model)
                    added_models += 1

                await session.commit()
                logger.info(f'Loaded {added_models} models for {creator.name}')
                return added_models > 0

    except Exception as e:
        logger.error(f"Error while load models: {str(e)}", exc_info=True)
        
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                creator = await session.get(AiCreators, creator_id)
                if creator:
                    await session.delete(creator)
                    await session.commit()
                    logger.info(f'Provider {creator.name} have not models')
        
        return False

def get_async_session():
    return async_sessionmaker(engine, expire_on_commit=False)()

async def get_selected_ai_creator():
    async with get_async_session() as session:
        result = await session.execute(
            select(Models).where(Models.selected == True)
        )
        selected_model = result.scalar_one_or_none()
        if selected_model:
            selected_ai_creator_result = await session.execute(
                select(AiCreators).where(AiCreators.id == selected_model.ai_creator_id)
            )
            selected_ai_creator = selected_ai_creator_result.scalar_one_or_none()
            if selected_ai_creator:
                return selected_ai_creator
            return None
        return None

async def create_defaults_settings(session):
    result = await session.execute(select(AiSettings))
    settings = result.scalars().first()
    if not settings:
        settings = AiSettings(
            temperature=0.7,
            prompt=Config.DEFAULT_PROMPT
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)