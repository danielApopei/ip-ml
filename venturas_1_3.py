import flask
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import aliased
from sqlalchemy import func
from fuzzywuzzy import process
from sqlalchemy.ext.hybrid import hybrid_property

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = ('postgresql://postgres:assword123@'
                                         'bd-dev.c9y4wsaswav8.us-east-1.rds.amazonaws.com:5432/BDdev')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# setup models
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    username = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email
        }

class Hotel(db.Model):
    __tablename__ = 'hotels'
    hotel_id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.String(50))
    address = db.Column(db.String(255))
    name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    website_url = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    city_id = db.Column(db.Integer)
    rating_location = db.Column(db.Float)
    rating_sleep = db.Column(db.Float)
    rating_rooms = db.Column(db.Float)
    rating_service = db.Column(db.Float)
    rating_value = db.Column(db.Float)
    rating_cleanliness = db.Column(db.Float)
    tripadvisor_price_level = db.Column(db.Integer)

    def to_dict(self):
        return {
            "hotel_id": self.hotel_id,
            "rating": self.rating,
            "address": self.address,
            "name": self.name,
            "description": self.description,
            "website_url": self.website_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city_id": self.city_id,
            "rating_location": self.rating_location,
            "rating_sleep": self.rating_sleep,
            "rating_rooms": self.rating_rooms,
            "rating_service": self.rating_service,
            "rating_value": self.rating_value,
            "rating_cleanliness": self.rating_cleanliness,
            "tripadvisor_price_level": self.tripadvisor_price_level
        }


class Amenity(db.Model):
    __tablename__ = 'amenities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }


class HotelAmenity(db.Model):
    __tablename__ = 'hotels_amenities'
    hotel_id = db.Column(db.Integer, db.ForeignKey('locations2.hotel_id'), primary_key=True)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenities.id'), primary_key=True)


class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    country_code = db.Column(db.String(3), db.ForeignKey('countries.code'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "country_code": self.country_code
        }


class Country(db.Model):
    __tablename__ = 'countries'
    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name
        }


class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('hotels.hotel_id'))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "location_id": self.location_id,
            "timestamp": self.timestamp
        }



with app.app_context():
    db.create_all()


def build_response(data):
    response = flask.jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/search', methods=['GET'])
def search_location():
    hotels_query = Hotel.query
    max_count = request.args.get("max_count")
    search_phrase = request.args.get("search_phrase")
    amenities = request.args.get("amenities")
    cities = request.args.get("cities")
    countries = request.args.get("countries")
    # min_rating = request.args.get("min_rating")
    min_rating_location = request.args.get("min_rating_location")
    min_rating_sleep = request.args.get("min_rating_sleep")
    min_rating_rooms = request.args.get("min_rating_rooms")
    min_rating_service = request.args.get("min_rating_service")
    min_rating_value = request.args.get("min_rating_value")
    min_rating_cleanliness = request.args.get("min_rating_cleanliness")
    if search_phrase:
        all_hotels = [hotel.name for hotel in Hotel.query.all()]
        best_match = process.extractBests(search_phrase, all_hotels, score_cutoff=80, limit=100)
        best_names = [match[0] for match in best_match]
        hotels_query = hotels_query.filter(Hotel.name.in_(best_names))
    if amenities:
        amenity_list = [amenity.strip() for amenity in amenities.split(',')]
        hotel_alias = aliased(Hotel)
        amenity_alias = aliased(Amenity)
        hotel_amenity_alias = aliased(HotelAmenity)

        subquery = db.session.query(
            hotel_amenity_alias.hotel_id,
            func.count(amenity_alias.id).label('amenity_count')
        ).join(amenity_alias, hotel_amenity_alias.amenity_id == amenity_alias.id
               ).filter(amenity_alias.name.in_(amenity_list)
                        ).group_by(hotel_amenity_alias.hotel_id
                                   ).subquery()
        hotels_query = hotels_query.join(subquery, Hotel.hotel_id == subquery.c.hotel_id
                                         ).filter(subquery.c.amenity_count == len(amenity_list))
    if cities:
        city_list = [city.strip() for city in cities.split(',')]
        city_subquery = db.session.query(City.id).filter(City.name.in_(city_list)).subquery()
        hotels_query = hotels_query.filter(Hotel.city_id.in_(city_subquery))
    if countries:
        country_list = [country.strip() for country in countries.split(',')]
        country_subquery = db.session.query(City.id).join(Country).filter(Country.name.in_(country_list)).subquery()
        hotels_query = hotels_query.filter(Hotel.city_id.in_(country_subquery))
    if min_rating_location:
        hotels_query = hotels_query.filter(Hotel.rating_location >= min_rating_location)
    if min_rating_sleep:
        hotels_query = hotels_query.filter(Hotel.rating_sleep >= min_rating_sleep)
    if min_rating_rooms:
        hotels_query = hotels_query.filter(Hotel.rating_rooms >= min_rating_rooms)
    if min_rating_service:
        hotels_query = hotels_query.filter(Hotel.rating_service >= min_rating_service)
    if min_rating_value:
        hotels_query = hotels_query.filter(Hotel.rating_value >= min_rating_value)
    if min_rating_cleanliness:
        hotels_query = hotels_query.filter(Hotel.rating_cleanliness >= min_rating_cleanliness)
    if max_count:
        max_count = int(max_count)
        hotels_query = hotels_query.limit(max_count)
    hotels = hotels_query.all()
    return build_response([hotel.to_dict() for hotel in hotels])


@app.route('/get_cities', methods=['GET'])
def get_cities():
    country_name = request.args.get('country')
    if not country_name:
        return build_response({"error": "Country name is required"}), 400
    country = Country.query.filter(Country.name.ilike(country_name)).first()
    if not country:
        return build_response({"error": "country param missing!"}), 404
    cities = City.query.filter_by(country_code=country.code).all()
    city_list = [city.to_dict() for city in cities]
    return build_response(city_list)


@app.route('/get_countries', methods=['GET'])
def get_countries():
    countries = Country.query.all()
    country_list = [country.to_dict() for country in countries]
    return build_response(country_list)


@app.route('/get_amenities', methods=['GET'])
def get_amenities():
    amenities = Amenity.query.all()
    amenity_list = [amenity.to_dict() for amenity in amenities]
    return build_response(amenity_list)

@app.route('/get_history', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return build_response({"error": "user_id is required"}), 400
    history = History.query.filter_by(user_id=user_id).all()
    history_list = [history.to_dict() for history in history]
    return build_response(history_list)


# <id> - id locatie accesata
@app.route('/location/<id>', methods=['POST'])
def view_location(id):
    user_id = request.args.get('user_id')
    location_id = id
    if not location_id:
        return build_response({"error": "location_id is required"}), 400
    #user_id - id ul user ului care acceseaza locatia
    if user_id:
        history = History(user_id=user_id, location_id=location_id)
        db.session.add(history)
        db.session.commit()
    hotels_query = Hotel.query.filter(Hotel.hotel_id == location_id)
    hotel = hotels_query.first()
    base_info = hotel.to_dict()

    hotel_alias = aliased(Hotel)
    amenity_alias = aliased(Amenity)
    hotel_amenity_alias = aliased(HotelAmenity)
    subquery = db.session.query(amenity_alias.name).join(hotel_amenity_alias, amenity_alias.id == hotel_amenity_alias.amenity_id
                                                         ).filter(hotel_amenity_alias.hotel_id == location_id).subquery()
    amenities = db.session.query(subquery.c.name).all()
    base_info['amenities'] = [amenity[0] for amenity in amenities]
    return build_response(base_info)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)