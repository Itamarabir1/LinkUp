DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS passenger_requests CASCADE;
DROP TABLE IF EXISTS rides CASCADE;
DROP TABLE IF EXISTS outbox_events CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS ride_status CASCADE;
DROP TYPE IF EXISTS booking_status CASCADE;
DROP TYPE IF EXISTS passenger_request_status CASCADE;

CREATE TYPE ride_status AS ENUM ('open', 'full', 'completed', 'cancelled');
CREATE TYPE booking_status AS ENUM ('pending_approval', 'confirmed', 'rejected', 'cancelled', 'completed');
CREATE TYPE passenger_request_status AS ENUM ('active', 'matched', 'expired', 'cancelled', 'pending', 'approved', 'rejected', 'completed');

CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    fcm_token TEXT,
    refresh_token TEXT,
    last_location GEOGRAPHY(POINT, 4326),
    avatar_url VARCHAR(500),
    last_login TIMESTAMP WITH TIME ZONE,
    last_active_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    invite_code VARCHAR(64) UNIQUE NOT NULL,
    admin_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    max_members INTEGER,
    invite_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(group_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_group_member UNIQUE (group_id, user_id)
);

CREATE TABLE rides (
    ride_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(group_id) ON DELETE SET NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_arrival_time TIMESTAMP WITH TIME ZONE,
    available_seats INTEGER NOT NULL DEFAULT 4 CHECK (available_seats BETWEEN 0 AND 8),
    price NUMERIC(10, 2) DEFAULT 0 CHECK (price >= 0),
    origin_name VARCHAR(255),
    origin_geom GEOGRAPHY(POINT, 4326) NOT NULL,
    destination_name VARCHAR(255),
    destination_geom GEOGRAPHY(POINT, 4326) NOT NULL,
    route_coords GEOGRAPHY(LINESTRING, 4326),
    route_summary VARCHAR(255),
    distance_km DECIMAL(10, 2),
    duration_min DECIMAL(10, 2),
    status ride_status DEFAULT 'open' NOT NULL,
    reminder_sent BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE passenger_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    passenger_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(group_id) ON DELETE SET NULL,
    num_passengers INTEGER NOT NULL DEFAULT 1 CHECK (num_passengers BETWEEN 1 AND 8),
    pickup_name VARCHAR(255),
    pickup_geom GEOGRAPHY(POINT, 4326) NOT NULL,
    destination_name VARCHAR(255),
    destination_geom GEOGRAPHY(POINT, 4326) NOT NULL,
    requested_departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_arrival_time TIMESTAMP WITH TIME ZONE,
    desired_arrival_time TIMESTAMP WITH TIME ZONE,
    search_radius_meters INTEGER DEFAULT 500 CHECK (search_radius_meters BETWEEN 100 AND 5000),
    is_auto_generated BOOLEAN DEFAULT FALSE,
    distance_km DECIMAL(10, 2) DEFAULT 0,
    duration_min DECIMAL(10, 2) DEFAULT 0,
    status passenger_request_status DEFAULT 'active' NOT NULL,
    is_notification_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_id UUID NOT NULL REFERENCES rides(ride_id) ON DELETE CASCADE,
    passenger_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    request_id UUID REFERENCES passenger_requests(request_id) ON DELETE SET NULL,
    num_seats INTEGER NOT NULL DEFAULT 1 CHECK (num_seats BETWEEN 1 AND 8),
    pickup_point GEOGRAPHY(POINT, 4326),
    pickup_time TIMESTAMP WITH TIME ZONE,
    pickup_name VARCHAR(255),
    status booking_status DEFAULT 'pending_approval' NOT NULL,
    reminder_sent BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT unique_passenger_per_ride UNIQUE (ride_id, passenger_id)
);

CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id_1 UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    user_id_2 UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_conversation_pair UNIQUE (user_id_1, user_id_2),
    CONSTRAINT ck_conversation_ordered CHECK (user_id_1 < user_id_2)
);

CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_conversations_user_1 ON conversations (user_id_1);
CREATE INDEX idx_conversations_user_2 ON conversations (user_id_2);
CREATE INDEX idx_messages_conversation ON messages (conversation_id);
CREATE INDEX idx_messages_created ON messages (conversation_id, created_at);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    targets VARCHAR[] NOT NULL,
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    idempotency_key VARCHAR(255) UNIQUE
);

CREATE TRIGGER update_user_modtime BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_ride_modtime BEFORE UPDATE ON rides FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_request_modtime BEFORE UPDATE ON passenger_requests FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_booking_modtime BEFORE UPDATE ON bookings FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TABLE chat_analysis (
    analysis_id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    driver_name VARCHAR(255),
    passenger_name VARCHAR(255),
    pickup_location TEXT,
    meeting_time TEXT,
    summary_hebrew TEXT,
    analysis_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_chat_analysis_conversation UNIQUE(conversation_id)
);

CREATE INDEX idx_chat_analysis_conversation ON chat_analysis (conversation_id);

CREATE INDEX idx_users_location ON users USING GIST(last_location);
CREATE INDEX idx_rides_origin_geom ON rides USING GIST(origin_geom);
CREATE INDEX idx_rides_destination_geom ON rides USING GIST(destination_geom);
CREATE INDEX idx_outbox_events_pending ON outbox_events (created_at) WHERE status = 'PENDING';
