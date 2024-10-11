import scrapy
import pymongo
import os


class GoodreadsSpider(scrapy.Spider):
    name = 'goodreads_spider'
    allowed_domains = ['goodreads.com']
    start_urls = [
        'https://www.goodreads.com/list/show/1.Best_Books_Ever?page=1'
    ]

    count = 0  # Đếm số dòng dữ liệu
    limit = 1003  # Giới hạn số dòng dữ liệu

    def __init__(self, *args, **kwargs):
        super(GoodreadsSpider, self).__init__(*args, **kwargs)

        # Sử dụng MONGO_URI từ biến môi trường
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client['goodreads_db']
        self.collection = self.db['books']

    def parse(self, response):
        books = response.css('tr[itemtype="http://schema.org/Book"]')

        for book in books:
            if self.count >= self.limit:
                break  # Dừng khi đủ 1000 dòng dữ liệu, nhưng tiếp tục hoàn tất trang hiện tại

            rank = book.css('td.number::text').get()
            title = book.css('a.bookTitle span::text').get()
            author = book.css('a.authorName span::text').get()

            score_text = book.css('span.smallText a::text').re_first(
                r'score: ([\d,]+)')
            score = score_text if score_text else 'Not Available'

            book_link = response.urljoin(
                book.css('a.bookTitle::attr(href)').get())
            yield scrapy.Request(book_link, callback=self.parse_book_details, meta={
                'rank': rank,
                'title': title,
                'author': author,
                'score': score
            })

            self.count += 1

        # In ra số lượng đã cào
        self.logger.info(f"Đã cào được {self.count} sách")

        # Phân trang - Tìm liên kết đến trang tiếp theo
        next_page = response.css(
            'div.pagination a.next_page::attr(href)').get()
        if next_page and self.count < self.limit:
            next_page_url = response.urljoin(next_page)
            yield scrapy.Request(next_page_url, callback=self.parse)

    def parse_book_details(self, response):
        rank = response.meta['rank']
        title = response.meta['title']
        author = response.meta['author']
        score = response.meta['score']

        rating = response.css(
            'div.RatingStatistics__rating::text').get() or 'Not Available'
        number_of_ratings = response.css(
            'span[data-testid="ratingsCount"]::text').re_first(r'([\d,]+)') or 'Not Available'
        date = response.css(
            'p[data-testid="publicationInfo"]::text').get() or 'Not Available'
        description = response.css(
            'div.DetailsLayoutRightParagraph__widthConstrained span.Formatted::text').get() or 'Not Available'
        reviews = response.css(
            'span[data-testid="reviewsCount"]::text').re_first(r'([\d,]+)') or 'Not Available'

        page_format = response.css('p[data-testid="pagesFormat"]::text').get()
        if page_format:
            pages, cover_type = page_format.split(',', 1)
            pages = pages.split()[0].strip()
            cover_type = cover_type.strip()
        else:
            pages = None
            cover_type = None

        # Cào thêm thông tin thể loại
        genres = response.css(
            'ul.CollapsableList .BookPageMetadataSection__genreButton .Button__labelItem::text').getall()
        genres = ', '.join(genres) if genres else 'Not Available'

        # Dữ liệu để lưu vào MongoDB
        book_data_mongo = {
            'Rank': rank,
            'Title': title,
            'Author': author,
            'Rating': rating,
            'Number of Ratings': number_of_ratings,
            'Date': date,
            'Description': description,
            'Reviews': reviews,
            'Pages': pages,
            'Cover Type': cover_type,
            'Score': score,
            'Genres': genres
        }

        # Lưu vào MongoDB
        self.collection.insert_one(book_data_mongo)

        # Dữ liệu để xuất ra CSV/JSON (không chứa _id)
        book_data_export = {
            'Rank': rank,
            'Title': title,
            'Author': author,
            'Rating': rating,
            'Number of Ratings': number_of_ratings,
            'Date': date,
            'Description': description,
            'Reviews': reviews,
            'Pages': pages,
            'Cover Type': cover_type,
            'Score': score,
            'Genres': genres
        }

        # Trả dữ liệu cho Scrapy để xuất ra file CSV/JSON
        yield book_data_export

    def close(self, reason):
        # Đóng kết nối MongoDB khi kết thúc cào dữ liệu
        self.client.close()
