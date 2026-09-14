CREATE PERSISTENT SECRET my_aws_secret (
    TYPE s3,
    PROVIDER credential_chain
);

SELECT * FROM read_csv('s3://phile-spotify1-transformed-data/albums/**/*.csv');
SELECT * FROM read_csv('s3://phile-spotify1-transformed-data/songs/**/*.csv');
SELECT * FROM read_csv('s3://phile-spotify1-transformed-data/artists/**/*.csv');