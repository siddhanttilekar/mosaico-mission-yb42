from mosaicolabs import MosaicoClient, IMU, QuerySequence, QueryTopic, QueryOntologyCatalog

with MosaicoClient.connect("localhost", 6726) as client:
    resp = client.query(
        QuerySequence().with_name("spot_yb42"),
        QueryTopic().with_name("/imu/body"),
        QueryOntologyCatalog(IMU.Q.acceleration.z.between([-1.0, 1.0])),
    )
    window = resp[0].topics[0].clusterize(clustering_dt_ns=100_000_000)[0]
    print(window.timerange.start)   # 1795181862000000000
