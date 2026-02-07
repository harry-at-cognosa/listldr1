--
-- PostgreSQL database dump
--

\restrict 5bjnZDr6NfIR9K2fVUR3L9Nb0Xg3omfjt1fHSycZYcYWtyCfLdgEG2TztbiV6H8

-- Dumped from database version 17.6 (Postgres.app)
-- Dumped by pg_dump version 17.6 (Postgres.app)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_settings (
    name character varying(100) NOT NULL,
    value text NOT NULL
);


--
-- Name: country; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country (
    country_id integer NOT NULL,
    country_abbr character(3) NOT NULL,
    country_name character varying(50) NOT NULL,
    currency_id integer,
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    country_enabled integer DEFAULT 1 NOT NULL
);


--
-- Name: country_conversion_pairs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.country_conversion_pairs (
    ccp_id integer NOT NULL,
    ccp_from_country_id integer NOT NULL,
    ccp_to_country_id integer NOT NULL
);


--
-- Name: country_conversion_pairs_ccp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_conversion_pairs_ccp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_conversion_pairs_ccp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_conversion_pairs_ccp_id_seq OWNED BY public.country_conversion_pairs.ccp_id;


--
-- Name: country_country_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.country_country_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_country_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.country_country_id_seq OWNED BY public.country.country_id;


--
-- Name: currency; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.currency (
    currency_id integer NOT NULL,
    currency_symbol character varying(3) NOT NULL,
    currency_name character varying(20),
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    currency_enabled integer DEFAULT 1 NOT NULL
);


--
-- Name: currency_currency_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.currency_currency_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: currency_currency_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.currency_currency_id_seq OWNED BY public.currency.currency_id;


--
-- Name: customer_quotes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_quotes (
    quote_id integer NOT NULL,
    country_id integer,
    currency_id integer,
    product_cat_id integer,
    product_line_id integer,
    current_blob_id bigint,
    source_template_id integer,
    cquote_name text,
    cquote_order_codes text,
    cquote_desc text,
    cquote_comment text,
    cquote_section_count integer DEFAULT 0 NOT NULL,
    cquote_fbo_location text,
    cquote_as_of_date date,
    cquote_extrn_file_ref text,
    cquote_active boolean DEFAULT true,
    cquote_version text,
    cquote_content text,
    cquote_status character varying(20) DEFAULT 'not started'::character varying,
    status_datetime timestamp with time zone,
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    cquote_enabled integer DEFAULT 1 NOT NULL,
    CONSTRAINT customer_quotes_status_chk CHECK (((cquote_status)::text = ANY ((ARRAY['not started'::character varying, 'in process'::character varying, 'in review'::character varying, 'approved'::character varying, 'sent'::character varying, 'accepted'::character varying, 'declined'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: customer_quotes_quote_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.customer_quotes_quote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customer_quotes_quote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.customer_quotes_quote_id_seq OWNED BY public.customer_quotes.quote_id;


--
-- Name: document_blob; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_blob (
    blob_id bigint NOT NULL,
    bytes bytea NOT NULL,
    sha256 bytea NOT NULL,
    size_bytes integer NOT NULL,
    content_type text NOT NULL,
    original_filename text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT document_blob_sha256_len CHECK ((octet_length(sha256) = 32)),
    CONSTRAINT document_blob_size_chk CHECK ((size_bytes = octet_length(bytes)))
);


--
-- Name: document_blob_blob_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_blob_blob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_blob_blob_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_blob_blob_id_seq OWNED BY public.document_blob.blob_id;


--
-- Name: document_blob_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_blob_history (
    history_id bigint NOT NULL,
    entity_type text NOT NULL,
    entity_id integer NOT NULL,
    blob_id bigint NOT NULL,
    replaced_at timestamp with time zone DEFAULT now() NOT NULL,
    replaced_by character varying(50),
    CONSTRAINT blob_history_entity_type_chk CHECK ((entity_type = ANY (ARRAY['template'::text, 'quote'::text])))
);


--
-- Name: document_blob_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_blob_history_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_blob_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_blob_history_history_id_seq OWNED BY public.document_blob_history.history_id;


--
-- Name: pconv_factor_values; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pconv_factor_values (
    pfv_id integer NOT NULL,
    pcf_id integer NOT NULL,
    ccp_id integer NOT NULL,
    pfc_from_date date DEFAULT CURRENT_DATE NOT NULL,
    pfc_to_date date DEFAULT '2040-12-31'::date NOT NULL,
    pfc_multiplier_1 numeric(8,4) DEFAULT 1.0 NOT NULL,
    pfc_multiplier_2 numeric(8,4) DEFAULT 1.0 NOT NULL,
    CONSTRAINT pconv_date_order CHECK ((pfc_from_date <= pfc_to_date))
);


--
-- Name: pconv_factor_values_pfv_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pconv_factor_values_pfv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pconv_factor_values_pfv_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pconv_factor_values_pfv_id_seq OWNED BY public.pconv_factor_values.pfv_id;


--
-- Name: plsq_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plsq_templates (
    plsqt_id integer NOT NULL,
    country_id integer,
    currency_id integer,
    product_cat_id integer,
    product_line_id integer,
    plsqt_name text,
    plsqt_order_codes text,
    plsqt_desc text,
    plsqt_comment text,
    plsqt_section_count integer DEFAULT 0 NOT NULL,
    plsqt_fbo_location text,
    plsqt_as_of_date date,
    plsqt_extrn_file_ref text,
    plsqt_active boolean DEFAULT true,
    plsqt_version text,
    plsqt_content text,
    plsqt_status character varying(20) DEFAULT 'not started'::character varying,
    status_datetime timestamp with time zone,
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    plsqt_enabled integer DEFAULT 1 NOT NULL,
    current_blob_id bigint,
    CONSTRAINT plsq_templates_plsqt_status_check CHECK (((plsqt_status)::text = ANY (ARRAY[('not started'::character varying)::text, ('in process'::character varying)::text, ('in review'::character varying)::text, ('approved'::character varying)::text, ('cloned'::character varying)::text])))
);


--
-- Name: plsq_templates_plsqt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plsq_templates_plsqt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plsq_templates_plsqt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plsq_templates_plsqt_id_seq OWNED BY public.plsq_templates.plsqt_id;


--
-- Name: plsqt_sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plsqt_sections (
    plsqts_id integer NOT NULL,
    plsqt_id integer NOT NULL,
    section_type_id integer NOT NULL,
    plsqts_seqn integer NOT NULL,
    plsqts_alt_name text,
    plsqts_comment text,
    plsqts_use_alt_name boolean DEFAULT false,
    plsqts_subsection_count integer DEFAULT 0 NOT NULL,
    plsqts_active boolean DEFAULT true,
    plsqts_version text,
    plsqts_extrn_file_ref text,
    plsqts_content text,
    plsqts_status character varying(20) DEFAULT 'not started'::character varying,
    status_datetime timestamp with time zone,
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    plsqts_enabled integer DEFAULT 1 NOT NULL,
    CONSTRAINT plsqt_sections_plsqts_status_check CHECK (((plsqts_status)::text = ANY (ARRAY[('not started'::character varying)::text, ('in process'::character varying)::text, ('in review'::character varying)::text, ('approved'::character varying)::text, ('cloned'::character varying)::text])))
);


--
-- Name: plsqt_sections_plsqts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plsqt_sections_plsqts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plsqt_sections_plsqts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plsqt_sections_plsqts_id_seq OWNED BY public.plsqt_sections.plsqts_id;


--
-- Name: plsqts_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plsqts_type (
    plsqtst_id integer NOT NULL,
    plsqtst_name character varying(50),
    plsqtst_has_total_price boolean DEFAULT false,
    plsqtst_has_lineitem_prices boolean DEFAULT false,
    plsqtst_comment character varying(100),
    extrn_file_ref character varying(500),
    plsqtst_active boolean DEFAULT true,
    plsqtst_version character varying(25),
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50)
);


--
-- Name: plsqts_type_plsqtst_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plsqts_type_plsqtst_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plsqts_type_plsqtst_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plsqts_type_plsqtst_id_seq OWNED BY public.plsqts_type.plsqtst_id;


--
-- Name: price_conv_factors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.price_conv_factors (
    pcf_id integer NOT NULL,
    pc_factor_code character varying(3) NOT NULL,
    pc_factor_description character varying(40)
);


--
-- Name: price_conv_factors_pcf_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.price_conv_factors_pcf_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: price_conv_factors_pcf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.price_conv_factors_pcf_id_seq OWNED BY public.price_conv_factors.pcf_id;


--
-- Name: product_cat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_cat (
    product_cat_id integer NOT NULL,
    product_cat_abbr character(3),
    product_cat_name character varying(50),
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    product_cat_enabled integer DEFAULT 1 NOT NULL
);


--
-- Name: product_cat_product_cat_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.product_cat_product_cat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_cat_product_cat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.product_cat_product_cat_id_seq OWNED BY public.product_cat.product_cat_id;


--
-- Name: product_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_line (
    product_line_id integer NOT NULL,
    product_cat_id integer NOT NULL,
    product_line_abbr character(3),
    product_line_name character varying(20),
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    product_line_enabled integer DEFAULT 1 NOT NULL
);


--
-- Name: product_line_product_line_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.product_line_product_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_line_product_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.product_line_product_line_id_seq OWNED BY public.product_line.product_line_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password character varying(255) NOT NULL,
    role character varying(20) DEFAULT 'user'::character varying NOT NULL,
    last_update_datetime timestamp with time zone,
    last_update_user character varying(50),
    user_enabled integer DEFAULT 1 NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY (ARRAY[('admin'::character varying)::text, ('user'::character varying)::text])))
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: country country_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country ALTER COLUMN country_id SET DEFAULT nextval('public.country_country_id_seq'::regclass);


--
-- Name: country_conversion_pairs ccp_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_conversion_pairs ALTER COLUMN ccp_id SET DEFAULT nextval('public.country_conversion_pairs_ccp_id_seq'::regclass);


--
-- Name: currency currency_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency ALTER COLUMN currency_id SET DEFAULT nextval('public.currency_currency_id_seq'::regclass);


--
-- Name: customer_quotes quote_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes ALTER COLUMN quote_id SET DEFAULT nextval('public.customer_quotes_quote_id_seq'::regclass);


--
-- Name: document_blob blob_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob ALTER COLUMN blob_id SET DEFAULT nextval('public.document_blob_blob_id_seq'::regclass);


--
-- Name: document_blob_history history_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob_history ALTER COLUMN history_id SET DEFAULT nextval('public.document_blob_history_history_id_seq'::regclass);


--
-- Name: pconv_factor_values pfv_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pconv_factor_values ALTER COLUMN pfv_id SET DEFAULT nextval('public.pconv_factor_values_pfv_id_seq'::regclass);


--
-- Name: plsq_templates plsqt_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates ALTER COLUMN plsqt_id SET DEFAULT nextval('public.plsq_templates_plsqt_id_seq'::regclass);


--
-- Name: plsqt_sections plsqts_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqt_sections ALTER COLUMN plsqts_id SET DEFAULT nextval('public.plsqt_sections_plsqts_id_seq'::regclass);


--
-- Name: plsqts_type plsqtst_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqts_type ALTER COLUMN plsqtst_id SET DEFAULT nextval('public.plsqts_type_plsqtst_id_seq'::regclass);


--
-- Name: price_conv_factors pcf_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.price_conv_factors ALTER COLUMN pcf_id SET DEFAULT nextval('public.price_conv_factors_pcf_id_seq'::regclass);


--
-- Name: product_cat product_cat_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_cat ALTER COLUMN product_cat_id SET DEFAULT nextval('public.product_cat_product_cat_id_seq'::regclass);


--
-- Name: product_line product_line_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_line ALTER COLUMN product_line_id SET DEFAULT nextval('public.product_line_product_line_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: app_settings app_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_pkey PRIMARY KEY (name);


--
-- Name: country_conversion_pairs country_conversion_pairs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_conversion_pairs
    ADD CONSTRAINT country_conversion_pairs_pkey PRIMARY KEY (ccp_id);


--
-- Name: country country_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_pkey PRIMARY KEY (country_id);


--
-- Name: currency currency_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency
    ADD CONSTRAINT currency_pkey PRIMARY KEY (currency_id);


--
-- Name: customer_quotes customer_quotes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_pkey PRIMARY KEY (quote_id);


--
-- Name: document_blob_history document_blob_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob_history
    ADD CONSTRAINT document_blob_history_pkey PRIMARY KEY (history_id);


--
-- Name: document_blob document_blob_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob
    ADD CONSTRAINT document_blob_pkey PRIMARY KEY (blob_id);


--
-- Name: document_blob document_blob_sha256_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob
    ADD CONSTRAINT document_blob_sha256_unique UNIQUE (sha256);


--
-- Name: pconv_factor_values pconv_factor_values_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pconv_factor_values
    ADD CONSTRAINT pconv_factor_values_pkey PRIMARY KEY (pfv_id);


--
-- Name: pconv_factor_values pconv_no_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pconv_factor_values
    ADD CONSTRAINT pconv_no_overlap EXCLUDE USING gist (pcf_id WITH =, ccp_id WITH =, daterange(pfc_from_date, pfc_to_date, '[]'::text) WITH &&);


--
-- Name: plsq_templates plsq_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_pkey PRIMARY KEY (plsqt_id);


--
-- Name: plsqt_sections plsqt_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqt_sections
    ADD CONSTRAINT plsqt_sections_pkey PRIMARY KEY (plsqts_id);


--
-- Name: plsqts_type plsqts_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqts_type
    ADD CONSTRAINT plsqts_type_pkey PRIMARY KEY (plsqtst_id);


--
-- Name: price_conv_factors price_conv_factors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.price_conv_factors
    ADD CONSTRAINT price_conv_factors_pkey PRIMARY KEY (pcf_id);


--
-- Name: product_cat product_cat_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_cat
    ADD CONSTRAINT product_cat_pkey PRIMARY KEY (product_cat_id);


--
-- Name: product_line product_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_line
    ADD CONSTRAINT product_line_pkey PRIMARY KEY (product_line_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_blob_history_blob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_blob_history_blob ON public.document_blob_history USING btree (blob_id);


--
-- Name: idx_blob_history_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_blob_history_entity ON public.document_blob_history USING btree (entity_type, entity_id);


--
-- Name: idx_ccp_from_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ccp_from_country ON public.country_conversion_pairs USING btree (ccp_from_country_id);


--
-- Name: idx_ccp_pair_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_ccp_pair_unique ON public.country_conversion_pairs USING btree (ccp_from_country_id, ccp_to_country_id);


--
-- Name: idx_ccp_to_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ccp_to_country ON public.country_conversion_pairs USING btree (ccp_to_country_id);


--
-- Name: idx_country_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_country_currency ON public.country USING btree (currency_id);


--
-- Name: idx_cquotes_blob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cquotes_blob ON public.customer_quotes USING btree (current_blob_id);


--
-- Name: idx_cquotes_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cquotes_country ON public.customer_quotes USING btree (country_id);


--
-- Name: idx_cquotes_product_cat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cquotes_product_cat ON public.customer_quotes USING btree (product_cat_id);


--
-- Name: idx_cquotes_product_line; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cquotes_product_line ON public.customer_quotes USING btree (product_line_id);


--
-- Name: idx_cquotes_source_tmpl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cquotes_source_tmpl ON public.customer_quotes USING btree (source_template_id);


--
-- Name: idx_pfv_ccp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pfv_ccp ON public.pconv_factor_values USING btree (ccp_id);


--
-- Name: idx_pfv_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pfv_dates ON public.pconv_factor_values USING btree (pfc_from_date, pfc_to_date);


--
-- Name: idx_pfv_factor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pfv_factor ON public.pconv_factor_values USING btree (pcf_id);


--
-- Name: idx_product_line_cat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_product_line_cat ON public.product_line USING btree (product_cat_id);


--
-- Name: idx_sections_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_template ON public.plsqt_sections USING btree (plsqt_id);


--
-- Name: idx_sections_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_type ON public.plsqt_sections USING btree (section_type_id);


--
-- Name: idx_templates_blob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_blob ON public.plsq_templates USING btree (current_blob_id);


--
-- Name: idx_templates_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_country ON public.plsq_templates USING btree (country_id);


--
-- Name: idx_templates_product_cat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_product_cat ON public.plsq_templates USING btree (product_cat_id);


--
-- Name: idx_templates_product_line; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_product_line ON public.plsq_templates USING btree (product_line_id);


--
-- Name: country_conversion_pairs country_conversion_pairs_ccp_from_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_conversion_pairs
    ADD CONSTRAINT country_conversion_pairs_ccp_from_country_id_fkey FOREIGN KEY (ccp_from_country_id) REFERENCES public.country(country_id);


--
-- Name: country_conversion_pairs country_conversion_pairs_ccp_to_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country_conversion_pairs
    ADD CONSTRAINT country_conversion_pairs_ccp_to_country_id_fkey FOREIGN KEY (ccp_to_country_id) REFERENCES public.country(country_id);


--
-- Name: country country_currency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_currency_id_fkey FOREIGN KEY (currency_id) REFERENCES public.currency(currency_id);


--
-- Name: customer_quotes customer_quotes_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_country_id_fkey FOREIGN KEY (country_id) REFERENCES public.country(country_id);


--
-- Name: customer_quotes customer_quotes_currency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_currency_id_fkey FOREIGN KEY (currency_id) REFERENCES public.currency(currency_id);


--
-- Name: customer_quotes customer_quotes_current_blob_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_current_blob_id_fkey FOREIGN KEY (current_blob_id) REFERENCES public.document_blob(blob_id);


--
-- Name: customer_quotes customer_quotes_product_cat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_product_cat_id_fkey FOREIGN KEY (product_cat_id) REFERENCES public.product_cat(product_cat_id);


--
-- Name: customer_quotes customer_quotes_product_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_product_line_id_fkey FOREIGN KEY (product_line_id) REFERENCES public.product_line(product_line_id);


--
-- Name: customer_quotes customer_quotes_source_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_quotes
    ADD CONSTRAINT customer_quotes_source_template_id_fkey FOREIGN KEY (source_template_id) REFERENCES public.plsq_templates(plsqt_id);


--
-- Name: document_blob_history document_blob_history_blob_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_blob_history
    ADD CONSTRAINT document_blob_history_blob_id_fkey FOREIGN KEY (blob_id) REFERENCES public.document_blob(blob_id);


--
-- Name: pconv_factor_values pconv_factor_values_ccp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pconv_factor_values
    ADD CONSTRAINT pconv_factor_values_ccp_id_fkey FOREIGN KEY (ccp_id) REFERENCES public.country_conversion_pairs(ccp_id);


--
-- Name: pconv_factor_values pconv_factor_values_pcf_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pconv_factor_values
    ADD CONSTRAINT pconv_factor_values_pcf_id_fkey FOREIGN KEY (pcf_id) REFERENCES public.price_conv_factors(pcf_id);


--
-- Name: plsq_templates plsq_templates_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_country_id_fkey FOREIGN KEY (country_id) REFERENCES public.country(country_id);


--
-- Name: plsq_templates plsq_templates_currency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_currency_id_fkey FOREIGN KEY (currency_id) REFERENCES public.currency(currency_id);


--
-- Name: plsq_templates plsq_templates_current_blob_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_current_blob_id_fkey FOREIGN KEY (current_blob_id) REFERENCES public.document_blob(blob_id);


--
-- Name: plsq_templates plsq_templates_product_cat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_product_cat_id_fkey FOREIGN KEY (product_cat_id) REFERENCES public.product_cat(product_cat_id);


--
-- Name: plsq_templates plsq_templates_product_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsq_templates
    ADD CONSTRAINT plsq_templates_product_line_id_fkey FOREIGN KEY (product_line_id) REFERENCES public.product_line(product_line_id);


--
-- Name: plsqt_sections plsqt_sections_plsqt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqt_sections
    ADD CONSTRAINT plsqt_sections_plsqt_id_fkey FOREIGN KEY (plsqt_id) REFERENCES public.plsq_templates(plsqt_id) ON DELETE CASCADE;


--
-- Name: plsqt_sections plsqt_sections_section_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plsqt_sections
    ADD CONSTRAINT plsqt_sections_section_type_id_fkey FOREIGN KEY (section_type_id) REFERENCES public.plsqts_type(plsqtst_id);


--
-- Name: product_line product_line_product_cat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_line
    ADD CONSTRAINT product_line_product_cat_id_fkey FOREIGN KEY (product_cat_id) REFERENCES public.product_cat(product_cat_id);


--
-- PostgreSQL database dump complete
--

\unrestrict 5bjnZDr6NfIR9K2fVUR3L9Nb0Xg3omfjt1fHSycZYcYWtyCfLdgEG2TztbiV6H8

