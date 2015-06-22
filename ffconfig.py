#
# configuration for flowfall
#

ofswitches = [
    {
        "dpid" : 1, # pf5459-1.nfv
        "servicebit" : False,
        "vlan" : {
            115 : {
                "vnf_up_ports" : [],

                "vnf_down_ports" : [
                    {
                        "port_num" : 3, "tagged" : False,
                        "mac" : [ None ]
                        },
                    {
                        "port_num" : 4, "tagged" : False,
                        "mac" : [ None ]
                        },
                ],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ "00:12:e2:46:4a:00" ] }, ],

                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ None ] }, ],

                },
            116 : {
                "vnf_up_ports" : [],

                "vnf_down_ports" : [
                    {
                        "port_num" : 68, "tagged" : False,
                        "mac" : [ None ]
                        },
                    {
                        "port_num" : 69, "tagged" : False,
                        "mac" : [ None ]
                        },
                ],

                "non_up_ports" :
                [ { "port_num" : 66, "tagged" : True,
                    "mac" : [ "78:48:59:33:18:32" ] }, ],

                "non_down_ports" :
                [ { "port_num" : 67, "tagged" : True,
                    "mac" : [ None ] }, ],

                },
            }
        },
    {
        "dpid" : 2, # pf5459-2.nfv
        "servicebit" : 3,
        "vlan" : {
            115 : {

                "vnf_up_ports" : [
                    {
                        "port_num" : 3, "tagged" : False,
                        "mac" : [ None ]
                    },
                    {
                        "port_num" : 4, "tagged" : False,
                        "mac" : [ None ]
                    },
                ],

                "vnf_down_ports" : [],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ None ] }, ],

                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ "f0:1c:2d:f6:db:00" ] }, ],
            },
            116 : {

                "vnf_up_ports" : [
                    {
                        "port_num" : 68, "tagged" : False,
                        "mac" : [ None ]
                    },
                    {
                        "port_num" : 69, "tagged" : False,
                        "mac" : [ None ]
                    },
                ],

                "vnf_down_ports" : [],

                "non_up_ports" :
                [ { "port_num" : 66, "tagged" : True,
                    "mac" : [ None ] }, ],

                "non_down_ports" :
                [ { "port_num" : 67, "tagged" : True,
                    "mac" : [ "f0:1c:2d:f6:db:00" ] }, ]
            },
        }
    },

    {
        "dpid" : 3, # pf5248-1.nfv
        "servicebit" : 5,
        "vlan" : {
            115 : {
                "vnf_up_ports" : [
                    # XXX: port_num 3 for A10 should be configured here
                    # XXX: port_num 4 for A10 should be configured here
                ],
                "vnf_down_ports" : [
                    {
                        "port_num" : 5, "tagged" : False,
                        "mac" : [ 
                            "02:00:ee:02:01:01", "02:00:ee:02:01:02",
                            "02:00:ee:02:01:03", "02:00:ee:02:01:04",
                            "02:00:ee:02:01:05", "02:00:ee:02:01:06",
                            "02:00:ee:02:01:07", "02:00:ee:02:01:08",
                        ]
                    },
                    {
                        "port_num" : 6, "tagged" : False,
                        "mac" : [ 
                            "02:00:ee:02:02:01", "02:00:ee:02:02:02",
                            "02:00:ee:02:02:03", "02:00:ee:02:02:04",
                            "02:00:ee:02:02:05", "02:00:ee:02:02:06",
                            "02:00:ee:02:02:07", "02:00:ee:02:02:08",
                        ]
                    },
                ],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ None ] }, ],
                
                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ None ] }, ],
            },
        }
    },
    {
        "dpid" : 4, # pf5248-2.nfv
        "servicebit" : 5,
        "vlan" : {
            116 : {
                "vnf_up_ports" : [
                    # XXX: port_num 3 for A10 should be configured here
                    # XXX: port_num 4 for A10 should be configured here
                ],
                "vnf_down_ports" : [
                    {
                        "port_num" : 5, "tagged" : False,
                        "mac" : [ 
                            "02:00:ee:02:03:01", "02:00:ee:02:03:02",
                            "02:00:ee:02:03:03", "02:00:ee:02:03:04",
                            "02:00:ee:02:03:05", "02:00:ee:02:03:06",
                            "02:00:ee:02:03:07", "02:00:ee:02:03:08",
                        ]
                    },
                    {
                        "port_num" : 6, "tagged" : False,
                        "mac" : [ 
                            "02:00:ee:02:03:01", "02:00:ee:02:03:02",
                            "02:00:ee:02:03:03", "02:00:ee:02:03:04",
                            "02:00:ee:02:03:05", "02:00:ee:02:03:06",
                            "02:00:ee:02:03:07", "02:00:ee:02:03:08",
                        ]
                    },
                ],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ None ] }, ],
                
                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ None ] }, ],
            },
        }
    },
    {
        "dpid" : 5, # pf5248-3.nfv
        "servicebit" : 4,
        "vlan" : {
            115 : {
                "vnf_up_ports" : [
                    {
                        "port_num" : 3, "tagged" : False,
                        "mac" : [
                            "02:00:ff:02:01:01", "02:00:ff:02:01:02",
                            "02:00:ff:02:01:03", "02:00:ff:02:01:04",
                        ]
                    },
                    # XXX: port_num 4 should be configured here
                ],
                "vnf_down_ports" : [
                    {
                        "port_num" : 5, "tagged" : False,
                        "mac" : [ None ]
                    },
                    {
                        "port_num" : 6, "tagged" : False,
                        "mac" : [ None ]
                    },
                ],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ None ] }, ],
                
                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ None ] }, ],
            },
        }
    },
    {
        "dpid" : 6, # pf5248-4.nfv
        "servicebit" : 4,
        "vlan" : {
            116 : {
                "vnf_up_ports" : [
                    # XXX: port_num 3 should be configured here
                    # XXX: port_num 4 should be configured here
                ],
                "vnf_down_ports" : [
                    {
                        "port_num" : 5, "tagged" : False,
                        "mac" : [ None ]
                    },
                    {
                        "port_num" : 6, "tagged" : False,
                        "mac" : [ None ]
                    },
                ],

                "non_up_ports" :
                [ { "port_num" : 1, "tagged" : True,
                    "mac" : [ None ] }, ],
                
                "non_down_ports" :
                [ { "port_num" : 2, "tagged" : True,
                    "mac" : [ None ] }, ],
            },
        }
    },
]



prefixes = [
    { "prefix" : "130.129.0.0/16", "type" : "CLIENT", },
    ]
