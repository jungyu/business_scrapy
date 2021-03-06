# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import loguru
import json
import time
from datetime import datetime

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from itemadapter import ItemAdapter

import sqlalchemy
import sqlalchemy.ext.automap
from .database.connection import session, metadata, automap

from .conversion.wordpress import Wordpress

class BusinessScrapyPipeline:
    __articletable__ = 'crawler_article'
    __articlemetatable__ = 'crawler_articlemeta'
    __fieldstable__ = 'crawler_fields'
    __listtable__ = 'crawler_list'
    __mediatable__ = 'crawler_media'

    def process_item(self, item, spider):
        loguru.logger.info(item['title'])

        if self.find_duplicate(item) == True:
            return item

        created = int(time.mktime(datetime.now().timetuple()))

        sqlalchemy.Table(self.__listtable__, metadata, autoload=True)
        sqlalchemy.Table(self.__articletable__, metadata, autoload=True)
        sqlalchemy.Table(self.__articlemetatable__, metadata, autoload=True)

        Article = automap.classes[self.__articletable__]
        Alist = automap.classes[self.__listtable__]
        ArticleMeta = automap.classes[self.__articlemetatable__]

        alist = Alist()
        alist.source_id = item['source_id']
        alist.topic = item['topics']
        alist.article_title = item['title']
        alist.article_url = item['article_url']
        alist.created = created
        session.add(alist)
        session.flush()

        article = Article()
        article.list_id = alist.id
        article.source_url = item['article_url']
        article.title = item['title']
        article.source_content = item['description']
        article.created = created
        session.add(article)
        session.flush()

        articleMeta = ArticleMeta()
        articleMeta.article_id = article.id
        articleMeta.meta_key = 'publish_date'
        articleMeta.meta_value = item['publish_date']
        session.add(articleMeta)
        session.flush()
   
        return item

    def close_spider(self, spider):
        try:
            session.commit()
        except Exception as e:
            loguru.logger.error('新增資料失敗')
            loguru.logger.error(e)
            session.rollback()
        finally:
            session.close()
            loguru.logger.info('完成 pipelines.')

    def find_duplicate(self, item):
        sqlalchemy.Table(self.__listtable__, metadata, autoload=True)
        Alist = automap.classes[self.__listtable__]

        aList = session.query(
            Alist
        ).filter(
            Alist.source_id == item['source_id'],
            Alist.article_title == item['title'],
            Alist.article_url == item['article_url']
        ).first()

        if aList:
            loguru.logger.info('Find duplicate source article: ' + str(aList.id))
            return True
        else:
            return False            
