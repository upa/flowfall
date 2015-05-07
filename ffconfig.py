#
# configuration for flowfall
#

ofswitches = [
    {
        "dpid" : 1,
        "servicebit" : 1,
        "vlan" : {
            115 : {
                "vnf_up_ports" : [
                    {
                        "port_num" : 49,
                        "tagged" : False,
                        "mac" : [ "00:01:01:01:02:00", "00:01:01:01:02:01",
                                  "00:01:01:01:02:02", "00:01:01:01:02:03",
                                  "00:01:01:01:02:04", "00:01:01:01:02:05",
                                  "00:01:01:01:02:06", "00:01:01:01:02:07",
                                  ]
                        },
                    ],

                "vnf_down_ports" : [],

                "non_up_ports" :
                [ { "port_num" : 50, "tagged" : True,
                    "mac" : [ "90:e2:ba:2c:e9:58" ] }, ],

                "non_down_ports" :
                [ { "port_num" : 51, "tagged" : False,
                    "mac" : [ "90:e2:ba:2c:e9:58" ] }, ],

                },
            }
        },
    {
        "dpid" : 2,
        "servicebit" : False,
        "vlan" : {
            115 : {

                "vnf_up_ports" : [],

                "vnf_down_ports" : [
                    {
                        "port_num" : 50,
                        "tagged" : False,
                        "mac" : [ "00:01:01:01:01:00", "00:01:01:01:01:01",
                                  "00:01:01:01:01:02", "00:01:01:01:01:03",
                                  "00:01:01:01:01:04", "00:01:01:01:01:05",
                                  "00:01:01:01:01:06", "00:01:01:01:01:07",
                                  ]
                        },
                    ],

                "non_up_ports" :
                    [ { "port_num" : 3, "tagged" : True,
                        "mac" : [ "00:01:01:01:02:00" ] }, ],

                "non_down_ports" :
                    [ { "port_num" : 47, "tagged" : True,
                        "mac" : [ "90:e2:ba:2c:e9:58" ] }, ],

                },
            }
        }
    ]



prefixes = [
    { "prefix" : "45.0.100.0/24", "type" : "CLIENT", },
    { "prefix" : "45.0.101.0/24", "type" : "CLIENT", },
    ]
